from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Optional, Tuple
load_dotenv()  

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

def _tag_from_source_id(source_id: str) -> str:
    # "WHO_stress" -> "[WHO]"
    head = (source_id or "").split("_", 1)[0].upper()
    return f"[{head}]" if head else ""

def render_citations(hits: List[dict], allowed_tags: Optional[List[str]]) -> List[Tuple[str,str]]:
    # Collect tag -> url for the hits we actually used
    tag_to_url = {}
    for h in hits:
        sid = h.get("source_id", "")
        url = h.get("url", "")
        tag = _tag_from_source_id(sid)
        if tag and url:
            tag_to_url[tag] = url

    if not tag_to_url:
        return []

    # Prefer the order of allowed_tags if provided; otherwise alphabetical
    if allowed_tags:
        order = [f"[{t}]" for t in allowed_tags if f"[{t}]" in tag_to_url]
        return [(t, tag_to_url[t]) for t in order]
    else:
        return [(t, tag_to_url[t]) for t in sorted(tag_to_url.keys())]

def compose(user_msg: str, hits: list, empathy_level: int, tier: int, context_text: str | None = None, allowed_tags: Optional[List[str]] = None):
    """
    Compose a reply using EVIDENCE and optional prior-turn CONTEXT (for personalization only).
    """
    if tier == 3:
        # Belt-and-suspenders: never compose advice on crisis content
        return ("", [])

    if allowed_tags:
        tags_line = ", ".join(f"[{t}]" for t in allowed_tags)
    else:
        inferred = sorted({ _tag_from_source_id(h.get("source_id","")).strip("[]") for h in hits if h.get("source_id") })
        tags_line = ", ".join(f"[{t}]" for t in inferred) if inferred else "[WHO], [CDC], [APA]"

    SYS = (
        "You are a careful, empathetic mental-health copilot for students with exam anxiety.\n"
        "Use only the provided EVIDENCE to make factual or actionable claims. If evidence is insufficient,\n"
        "say you can't answer and suggest a safe next step. CONTEXT is only for personalization and\n"
        "continuity (never as a source of facts).\n\n"
        "Tone: calm, validating, practical. Structure your reply as:\n"
        "1) Acknowledge (1-2 sentences),\n"
        "2) Explain (brief, evidence-grounded),\n"
        "3) Act (1-3 specific, low-effort steps).\n\n"
        f"Citations: use ONLY these tags when relevant — {tags_line}. "
        "Never invent new tags or include source IDs. Do not provide clinical diagnosis or medication advice. "
        "Avoid unsafe content. Never fabricate citations."
    )

    evidence = "\n".join(f"- {h.get('text','')}" for h in hits)
    context_text = context_text or "(no recent turns)"
    prompt = (
        f"EVIDENCE TAGS: {tags_line}\n\n"
        f"CONTEXT (do not cite from this):\n{context_text}\n\n"
        f"EVIDENCE (facts must come from here):\n{evidence}\n\n"
        f"USER: {user_msg}\nEmpathyLevel:{empathy_level}\nRiskTier:{tier}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYS},
                  {"role": "user", "content": prompt}],
        temperature=0.4,
    )
    text = resp.choices[0].message.content.strip()

    # Build citations from the hits we actually supplied
    tags = render_citations(hits, allowed_tags)
    # Optionally filter to allowed_tags (belt-and-suspenders)
    if allowed_tags:
        allowed = {f"[{t}]" for t in allowed_tags}
        tags = [(t, u) for (t, u) in tags if t in allowed]

    return text, tags
