from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Optional, Tuple

load_dotenv()

# Import tone analysis utilities
from core.tone import analyze_tone_and_cues, build_tone_block

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYS = """You are a careful, empathetic mental-health copilot for students with exam anxiety.
Use only the provided EVIDENCE to make factual or actionable claims. If evidence is insufficient,
say you can't answer and suggest a safe next step. CONTEXT is only for personalization and
continuity (never as a source of facts).

Tone: calm, validating, practical. Structure your reply as:
1) Acknowledge (1–2 sentences),
2) Explain (brief, evidence-grounded),
3) Act (1–3 specific, low-effort steps).

Citations: use ONLY the provided tags when relevant.
Never invent new tags or include source IDs. Never fabricate citations.
"""


def _tag_from_source_id(source_id: str) -> str:
    """WHO_stress -> [WHO]"""
    head = (source_id or "").split("_", 1)[0].upper()
    return f"[{head}]" if head else ""


def render_citations(hits: list, allowed_tags: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """
    Collect tag -> url for the hits we actually used
    """
    tag_to_url = {}
    for h in hits:
        sid = h.get("source_id", "")
        url = h.get("url", "")
        tag = _tag_from_source_id(sid)
        if tag and url:
            tag_to_url[tag] = url

    if not tag_to_url:
        return []

    # Prefer the order of allowed_tags if provided
    if allowed_tags:
        order = [f"[{t}]" for t in allowed_tags if f"[{t}]" in tag_to_url]
        return [(t, tag_to_url[t]) for t in order]
    else:
        return [(t, tag_to_url[t]) for t in sorted(tag_to_url.keys())]


def compose(
    user_msg: str,
    hits: list,
    empathy_level: int,
    tier: int,
    context_text: str | None = None,
    allowed_tags: Optional[List[str]] = None,  # FIXED: Added this parameter
    tone: dict | None = None,
):
    """
    Compose a reply using:
    - EVIDENCE chunks
    - CONTEXT (memory)
    - Tone/cue/template hints (optional)
    - Allowed citation tags
    """

    if tier == 3:
        return ("", [])

    evidence = "\n".join(f"- {h.get('text','')}" for h in hits)
    if not context_text:
        context_text = "(no recent turns)"

    # Build tone block
    if tone:
        tone_block = build_tone_block(tone)
    else:
        # Analyze tone from message
        tone_analysis = analyze_tone_and_cues(user_msg)
        tone_block = build_tone_block(tone_analysis)

    # Build allowed tags string
    if allowed_tags:
        tags_line = ", ".join(f"[{t}]" for t in allowed_tags)
    else:
        # Infer from hits
        inferred = sorted({_tag_from_source_id(h.get("source_id","")).strip("[]") for h in hits if h.get("source_id")})
        tags_line = ", ".join(f"[{t}]" for t in inferred) if inferred else "[WHO], [CDC], [APA]"

    legend = (
        f"EVIDENCE TAGS: {tags_line}\n"
        "Use CONTEXT only for personalization. Do NOT pull facts from context.\n"
        "Tone block helps you match warmth and focus.\n"
    )

    # Build prompt with tone block
    prompt = (
        f"{legend}\n\n"
        f"{tone_block}\n\n"
        f"CONTEXT (not factual source):\n{context_text}\n\n"
        f"EVIDENCE (facts must come from here):\n{evidence}\n\n"
        f"USER: {user_msg}\n"
        f"EmpathyLevel: {empathy_level}\nRiskTier: {tier}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )

    text = resp.choices[0].message.content.strip()
    tags = render_citations(hits, allowed_tags)
    return text, tags