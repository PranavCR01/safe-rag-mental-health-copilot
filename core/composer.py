from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()  

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

# System prompt tightened to treat CONTEXT only for personalization/continuity.
SYS = """You are a careful, empathetic mental-health copilot for students with exam anxiety.
Use only the provided EVIDENCE to make factual or actionable claims. If evidence is insufficient,
say you can’t answer and suggest a safe next step. CONTEXT is only for personalization and
continuity (never as a source of facts).

Tone: calm, validating, practical. Structure your reply as:
1) Acknowledge (1–2 sentences),
2) Explain (brief, evidence-grounded),
3) Act (1–3 specific, low-effort steps).

Citations: use ONLY these tags when relevant — [WHO], [CDC], [APA]. Never invent new tags or include source IDs.
Do not provide clinical diagnosis. Avoid unsafe content. Never fabricate citations.
"""

def render_citations(hits):
    # map source_id -> tag
    tag_map = {"WHO_stress":"[WHO]", "CDC_selfcare":"[CDC]", "APA_exam":"[APA]"}
    urls = {}
    for h in hits:
        tag = tag_map.get(h.get("source_id"))
        if tag and h.get("url"):
            urls[tag] = h["url"]
    ordered = [("[WHO]", urls.get("[WHO]")), ("[CDC]", urls.get("[CDC]")), ("[APA]", urls.get("[APA]"))]
    return [c for c in ordered if c[1]]

def compose(user_msg: str, hits: list, empathy_level: int, tier: int, context_text: str | None = None):
    """
    Compose a reply using EVIDENCE and optional prior-turn CONTEXT (for personalization only).
    """
    if tier == 3:
        # Belt-and-suspenders: never compose advice on crisis content
        return ("", [])

    evidence = "\n".join(f"- {h.get('text','')}" for h in hits)
    if not context_text:
        context_text = "(no recent turns)"

    legend = (
        "EVIDENCE TAGS: [WHO]=WHO stress guide; [CDC]=CDC self-care; [APA]=APA exam stress.\n"
        "Use CONTEXT only to keep continuity (e.g., prior worries, preferences)."
    )
    prompt = (
        f"{legend}\n\n"
        f"CONTEXT (do not cite from this):\n{context_text}\n\n"
        f"EVIDENCE (facts must come from here):\n{evidence}\n\n"
        f"USER: {user_msg}\nEmpathyLevel:{empathy_level}\nRiskTier:{tier}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYS},
                  {"role":"user","content":prompt}],
        temperature=0.4,
    )
    text = resp.choices[0].message.content.strip()
    tags = render_citations(hits)
    return text, tags
