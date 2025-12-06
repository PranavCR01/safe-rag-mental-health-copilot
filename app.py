import os, sqlite3, yaml, json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core.schema import ChatRequest, ChatResponse, Citation, RiskDetails, ToneAnalysis
from core.risk import classify_tier_with_confidence  # UPDATED: use confidence version
from core.tone import empathy_level
from core.retriever import search
from core.composer import compose
from core.safety import should_abstain, abstention_reply, red_flag

# --- LangChain memory for multi-turn context ---
from langchain_openai import ChatOpenAI
try:
    from langchain.memory import ConversationSummaryBufferMemory
except ImportError:
    try:
        from langchain_community.memory import ConversationSummaryBufferMemory
    except ImportError:
        print("Warning: Could not import ConversationSummaryBufferMemory, using simple memory")
        ConversationSummaryBufferMemory = None

# ===== extra imports for HITL review console =====
from fastapi import HTTPException, Query  
from fastapi.responses import StreamingResponse  
from core.schema import ReviewListItem, ReviewUpdate  
import csv, io

from core.persistent_memory import save_chat_turn, load_context_for_compose, get_conversation_history, get_user_conversation_stats

load_dotenv()
app = FastAPI(title="Safe Mental Health Copilot (Exam Anxiety)")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SOURCES = {s["id"]: s["url"] for s in yaml.safe_load(open("data/sources.yaml","r",encoding="utf-8"))}
def source_tag(source_id: str) -> str:
    return source_id.split("_", 1)[0].upper()

SOURCE_TAGS = {sid: source_tag(sid) for sid in SOURCES.keys()}
SOURCE_TAGS = sorted(set(SOURCE_TAGS.values()))

DB_PATH = "storage/audit_log.sqlite"

# -------- SQLite audit log WITH CONFIDENCE TRACKING --------
def init_db():
    os.makedirs("storage", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS chats(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT, tier INTEGER, abstained INTEGER,
        user_msg TEXT, model_reply TEXT, citations TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );""")
    
    cur = con.cursor()  
    cur.execute("PRAGMA table_info(chats);")  
    cols = {r[1] for r in cur.fetchall()}  
    
    # HITL columns
    if "reviewed" not in cols:  
        con.execute("ALTER TABLE chats ADD COLUMN reviewed INTEGER DEFAULT 0;")  
    if "label" not in cols:  
        con.execute("ALTER TABLE chats ADD COLUMN label TEXT;")  
    if "rating_empathy" not in cols:  
        con.execute("ALTER TABLE chats ADD COLUMN rating_empathy INTEGER;")  
    if "rating_factual" not in cols:  
        con.execute("ALTER TABLE chats ADD COLUMN rating_factual INTEGER;")  
    if "human_notes" not in cols:  
        con.execute("ALTER TABLE chats ADD COLUMN human_notes TEXT;")
    
    # NEW: Confidence tracking columns
    if "confidence" not in cols:
        con.execute("ALTER TABLE chats ADD COLUMN confidence REAL;")
    if "risk_details" not in cols:
        con.execute("ALTER TABLE chats ADD COLUMN risk_details TEXT;")
    
    con.commit()  
    con.close()


def init_mood_db():
    """Initialize mood tracking table"""
    con = sqlite3.connect(DB_PATH)
    
    con.execute("""
        CREATE TABLE IF NOT EXISTS mood_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            anxiety_level INTEGER NOT NULL,
            triggers TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    con.execute("CREATE INDEX IF NOT EXISTS idx_mood_user ON mood_entries(user_id)")
    con.commit()
    con.close()

init_db()
init_mood_db()

def save_chat(user_id, tier, abstained, user_msg, model_reply, citations, confidence=None, risk_details=None):
    """Save chat with confidence score and risk details"""
    con = sqlite3.connect(DB_PATH)
    risk_details_json = json.dumps(risk_details) if risk_details else None
    
    con.execute("""INSERT INTO chats(
        user_id, tier, abstained, user_msg, model_reply, citations, confidence, risk_details
    ) VALUES (?,?,?,?,?,?,?,?)""",
                (user_id, tier, 1 if abstained else 0, user_msg, model_reply, 
                 str(citations), confidence, risk_details_json))
    con.commit()
    con.close()

# -------- Per-user memory --------
class SimpleMemory:
    def __init__(self):
        self.history = []
    def load_memory_variables(self, inputs):
        return {"chat_history": "\n".join(self.history[-5:])}
    def save_context(self, inputs, outputs):
        self.history.append(f"User: {inputs.get('input', '')}")
        self.history.append(f"Assistant: {outputs.get('output', '')}")

_LLM = ChatOpenAI(model="gpt-4o-mini", temperature=0) if ConversationSummaryBufferMemory else None
_MEMORY: dict[str, any] = {}

def get_memory(user_id: str):
    mem = _MEMORY.get(user_id)
    if mem is None:
        if ConversationSummaryBufferMemory and _LLM:
            mem = ConversationSummaryBufferMemory(
                llm=_LLM,
                max_token_limit=1200,
                memory_key="chat_history",   
                return_messages=False
            )
        else:
            mem = SimpleMemory()
        _MEMORY[user_id] = mem
    return mem

def load_context(user_id: str) -> str:
    mem = get_memory(user_id)
    vars = mem.load_memory_variables({})
    return vars.get("chat_history", "")

def save_turn(user_id: str, user_msg: str, assistant_msg: str):
    mem = get_memory(user_id)
    mem.save_context({"input": user_msg}, {"output": assistant_msg})

# -------- Main endpoint WITH CONFIDENCE SCORING --------
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # 1) Load conversation context
    context_text = load_context_for_compose(req.user_id, format_type='full')

    # 2) Risk classification WITH CONFIDENCE
    tier, confidence, details = classify_tier_with_confidence(req.message)
    risk_details = RiskDetails(**details)

    from core.tone import analyze_tone_and_cues, build_tone_block
    tone_analysis_dict = analyze_tone_and_cues(req.message)
    tone_block_text = build_tone_block(tone_analysis_dict)
    
    # Create ToneAnalysis object
    tone_analysis = ToneAnalysis(
        empathy_level=tone_analysis_dict["empathy_level"],
        cues=tone_analysis_dict["cues"],
        template=tone_analysis_dict["template"],
        tone_block=tone_block_text
    )
    
    # 3) Early abstention for crisis
    if should_abstain(tier, had_evidence=True):
        if tier == 3:
            reply = abstention_reply(tier)
            save_chat(req.user_id, tier, True, req.message, reply, "[]", 
                     confidence=confidence, risk_details=details)
            save_chat_turn(req.user_id, req.message, text)
            return ChatResponse(
                text=reply, 
                citations=[], 
                tier=tier, 
                abstained=True,
                confidence=confidence,
                risk_details=risk_details,
                tone_analysis=tone_analysis 
            )

    # 4) Retrieval
    hits = search(req.message, k=4)
    had_evidence = len(hits) > 0
    if should_abstain(tier, had_evidence):
        reply = abstention_reply(tier)
        save_chat(req.user_id, tier, True, req.message, reply, "[]",
                 confidence=confidence, risk_details=details)
        save_chat_turn(req.user_id, req.message, text)
        return ChatResponse(
            text=reply, 
            citations=[], 
            tier=tier, 
            abstained=True,
            confidence=confidence,
            risk_details=risk_details,
            tone_analysis=tone_analysis 
        )

    # 5) Compose with CONTEXT
    text, tags = compose(
        req.message,
        hits,
        empathy_level(req.message),
        tier,
        context_text=context_text,
        allowed_tags=SOURCE_TAGS
    )

    # 6) Post-generation safety
    if red_flag(text):
        reply = abstention_reply(3)
        save_chat(req.user_id, 3, True, req.message, reply, "[]",
                 confidence=confidence, risk_details=details)
        save_chat_turn(req.user_id, req.message, text)
        return ChatResponse(
            text=reply, 
            citations=[], 
            tier=3, 
            abstained=True,
            confidence=confidence,
            risk_details=risk_details,
            tone_analysis=tone_analysis 
        )

    # 7) Render citations
    citations = []
    for tag, url in tags:
        citations.append(Citation(source_id=tag.strip("[]"), url=url))

    # 8) Save logs + update memory
    save_chat(req.user_id, tier, False, req.message, text, str(citations),
             confidence=confidence, risk_details=details)
    save_chat_turn(req.user_id, req.message, text)

    return ChatResponse(
        text=text, 
        citations=citations, 
        tier=tier, 
        abstained=False,
        confidence=confidence,
        risk_details=risk_details,
        tone_analysis=tone_analysis 
    )

# ======================================================
#             HITL REVIEW CONSOLE
# ======================================================  

def _dict_factory(cursor, row):  
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}  

@app.get("/conversation/history/{user_id}")
def get_user_history(user_id: str, limit: int = 20):
    history = get_conversation_history(user_id, limit=limit, hours_back=24*7)
    stats = get_user_conversation_stats(user_id)
    return {
        "user_id": user_id,
        "history": history,
        "stats": stats,
        "has_history": len(history) > 0
    }

@app.get("/reviews", response_model=list[ReviewListItem])  
def list_reviews(  
    status: str = Query("pending", pattern="^(pending|all)$"),  
    limit: int = 50,  
    user_id: str | None = None,  
):
    """List recent chats for human review."""  
    con = sqlite3.connect(DB_PATH)  
    con.row_factory = _dict_factory  
    cur = con.cursor()  
    q = "SELECT * FROM chats"  
    conds = []  
    args = []  
    if status == "pending":  
        conds.append("reviewed = 0")  
    if user_id:  
        conds.append("user_id = ?"); args.append(user_id)  
    if conds:  
        q += " WHERE " + " AND ".join(conds)  
    q += " ORDER BY id DESC LIMIT ?"  
    args.append(limit)  
    cur.execute(q, args)  
    rows = cur.fetchall()  
    con.close()  

    out = []  
    for r in rows:  
        r["abstained"] = bool(r.get("abstained", 0))  
        r["reviewed"] = bool(r.get("reviewed", 0))  
        out.append(ReviewListItem(**r))  
    return out  

@app.get("/reviews/{chat_id}", response_model=ReviewListItem)  
def get_review(chat_id: int):  
    con = sqlite3.connect(DB_PATH)  
    con.row_factory = _dict_factory  
    cur = con.cursor()  
    cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))  
    row = cur.fetchone()  
    con.close()  
    if not row:  
        raise HTTPException(404, "Chat not found")  
    row["abstained"] = bool(row.get("abstained", 0))  
    row["reviewed"] = bool(row.get("reviewed", 0))  
    return ReviewListItem(**row)  

@app.post("/reviews/{chat_id}", response_model=ReviewListItem)  
def update_review(chat_id: int, upd: ReviewUpdate):  
    con = sqlite3.connect(DB_PATH)  
    con.row_factory = _dict_factory  
    cur = con.cursor()  
    cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))  
    row = cur.fetchone()  
    if not row:  
        con.close()  
        raise HTTPException(404, "Chat not found")  

    fields = []  
    args = []  
    if upd.reviewed is not None:  
        fields.append("reviewed = ?"); args.append(1 if upd.reviewed else 0)  
    if upd.label is not None:  
        fields.append("label = ?"); args.append(upd.label)  
    if upd.rating_empathy is not None:  
        fields.append("rating_empathy = ?"); args.append(int(upd.rating_empathy))  
    if upd.rating_factual is not None:  
        fields.append("rating_factual = ?"); args.append(int(upd.rating_factual))  
    if upd.human_notes is not None:  
        fields.append("human_notes = ?"); args.append(upd.human_notes)  

    if fields:  
        q = "UPDATE chats SET " + ", ".join(fields) + " WHERE id = ?"  
        args.append(chat_id)  
        cur.execute(q, args)  
        con.commit()  

    cur.execute("SELECT * FROM chats WHERE id = ?", (chat_id,))  
    row2 = cur.fetchone()  
    con.close()  
    row2["abstained"] = bool(row2.get("abstained", 0))  
    row2["reviewed"] = bool(row2.get("reviewed", 0))  
    return ReviewListItem(**row2)  

@app.get("/metrics")  
def metrics():  
    """Quick counts/averages for reports WITH CONFIDENCE."""  
    con = sqlite3.connect(DB_PATH)  
    cur = con.cursor()  
    def one(q):  
        cur.execute(q); r = cur.fetchone()  
        return r[0] if r and r[0] is not None else 0  
    
    m = {  
        "total": one("SELECT COUNT(*) FROM chats"),  
        "reviewed": one("SELECT COUNT(*) FROM chats WHERE reviewed=1"),  
        "pending": one("SELECT COUNT(*) FROM chats WHERE reviewed=0"),  
        "label_safe": one("SELECT COUNT(*) FROM chats WHERE label='safe'"),  
        "label_unsafe": one("SELECT COUNT(*) FROM chats WHERE label='unsafe'"),  
        "label_low_empathy": one("SELECT COUNT(*) FROM chats WHERE label='low_empathy'"),  
        "label_hallucination": one("SELECT COUNT(*) FROM chats WHERE label='hallucination'"),  
        "avg_empathy": one("SELECT AVG(rating_empathy) FROM chats WHERE rating_empathy IS NOT NULL"),  
        "avg_factual": one("SELECT AVG(rating_factual) FROM chats WHERE rating_factual IS NOT NULL"),
        # NEW: Confidence metrics
        "avg_confidence": one("SELECT AVG(confidence) FROM chats WHERE confidence IS NOT NULL"),
        "avg_confidence_tier1": one("SELECT AVG(confidence) FROM chats WHERE tier=1 AND confidence IS NOT NULL"),
        "avg_confidence_tier2": one("SELECT AVG(confidence) FROM chats WHERE tier=2 AND confidence IS NOT NULL"),
        "avg_confidence_tier3": one("SELECT AVG(confidence) FROM chats WHERE tier=3 AND confidence IS NOT NULL"),
        "low_confidence_count": one("SELECT COUNT(*) FROM chats WHERE confidence < 0.5"),
    }
    con.close()  
    return m  

@app.get("/export/reviews.csv")  
def export_reviews_csv(status: str = Query("all", pattern="^(pending|all)$")):  
    """Download chats as CSV for offline review."""  
    con = sqlite3.connect(DB_PATH)  
    con.row_factory = _dict_factory  
    cur = con.cursor()  
    q = "SELECT * FROM chats"  
    if status == "pending":  
        q += " WHERE reviewed=0"  
    q += " ORDER BY id DESC"  
    cur.execute(q)  
    rows = cur.fetchall()  
    con.close()  

    buf = io.StringIO()  
    if rows:  
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))  
        writer.writeheader()  
        for r in rows: writer.writerow(r)  
    else:  
        buf.write("no_rows\n")  

    buf.seek(0)  
    return StreamingResponse(  
        iter([buf.read()]),  
        media_type="text/csv",  
        headers={"Content-Disposition": "attachment; filename=reviews.csv"},  
    )