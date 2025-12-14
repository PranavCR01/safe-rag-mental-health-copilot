

from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import List, Optional, Tuple

load_dotenv()

# Import tone analysis utilities
from core.tone import analyze_tone_and_cues, build_tone_block

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# IMPROVED SYSTEM PROMPT - More conversational and helpful
SYS = """You are a warm, supportive mental health companion for students dealing with exam anxiety.

CORE PRINCIPLES:
1. Write like a caring friend, not a clinical professional or textbook
2. Use natural, conversational language with contractions (I'm, you're, let's)
3. Vary your response structure - don't always follow the same pattern
4. Show empathy through understanding, not just acknowledging feelings
5. Be genuinely helpful - Only if someone asks you to create/help with something (schedule, plan, list), actually create it for them
6. Never prescribe medication/therapy or diagnose mental health conditions - Always suggest seeking licensed healthcare professional help and move on to the supportive conversation
7. Do not guarantee results - Encourage users to talk to trusted people

TONE GUIDELINES:
- High empathy (panic/crisis): Extra warm, reassuring, immediate action-focused
- Medium empathy: Supportive and encouraging
- Low empathy: Friendly and practical

FACTUAL CLAIMS:
- Use ONLY the provided EVIDENCE for factual statements
- CONTEXT is for personalization only (never cite context as a source)
- If evidence is insufficient, be honest and suggest next steps

PRACTICAL HELP:
- If asked to create something (schedule, plan, list) → Actually create it
- If asked for specific advice → Give specific, actionable steps
- If asked about their situation → Reference their context naturally

NATURAL CONVERSATION:
- Use "I understand..." not "It's completely understandable to..."
- Say "Let's..." not "Here are some steps..."
- Write "You're feeling overwhelmed" not "You are experiencing feelings of being overwhelmed"
- Avoid clinical language: symptoms, treatment plan, coping mechanisms, strategies
- Use everyday words: worried, stressed, feeling better, things that help

CITATIONS:
- Use only the provided tags: [WHO], [CDC], [APA]
- Integrate naturally into text, don't list separately
- Never invent sources or tags

Remember: You're here to help reduce anxiety, not increase it with formal language."""


def _tag_from_source_id(source_id: str) -> str:
    """WHO_stress -> [WHO]"""
    head = (source_id or "").split("_", 1)[0].upper()
    return f"[{head}]" if head else ""


def render_citations(hits: list, allowed_tags: Optional[List[str]] = None) -> List[Tuple[str, str]]:
    """Collect tag -> url for the hits we actually used"""
    tag_to_url = {}
    for h in hits:
        sid = h.get("source_id", "")
        url = h.get("url", "")
        tag = _tag_from_source_id(sid)
        if tag and url:
            tag_to_url[tag] = url

    if not tag_to_url:
        return []

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
    allowed_tags: Optional[List[str]] = None,
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
        context_text = "(no recent conversation history)"

    # Build tone block
    if tone:
        tone_block = build_tone_block(tone)
    else:
        tone_analysis = analyze_tone_and_cues(user_msg)
        tone_block = build_tone_block(tone_analysis)

    # Build allowed tags string
    if allowed_tags:
        tags_line = ", ".join(f"[{t}]" for t in allowed_tags)
    else:
        inferred = sorted({_tag_from_source_id(h.get("source_id","")).strip("[]") for h in hits if h.get("source_id")})
        tags_line = ", ".join(f"[{t}]" for t in inferred) if inferred else "[WHO], [CDC], [APA]"

    # IMPROVED PROMPT - More specific guidance
    legend = (
        f"AVAILABLE CITATION TAGS: {tags_line}\n\n"
        "IMPORTANT INSTRUCTIONS:\n"
        "- If the user asks you to CREATE something (schedule, plan, list, timetable), actually create it in detail\n"
        "- Use CONTEXT to personalize responses and reference previous conversation naturally\n"
        "- Use EVIDENCE for all factual claims - integrate citations naturally into your text\n"
        "- Write conversationally with contractions and natural language\n"
        "- Avoid clinical/formal language - write like a supportive friend\n"
        "- Vary your response structure based on what's most helpful\n"
    )

    # Build prompt with clear sections
    prompt = (
        f"{legend}\n"
        f"=== TONE & EMOTIONAL CONTEXT ===\n"
        f"{tone_block}\n\n"
        f"=== CONVERSATION HISTORY (for personalization only) ===\n"
        f"{context_text}\n\n"
        f"=== EVIDENCE (use for factual claims) ===\n"
        f"{evidence}\n\n"
        f"=== CURRENT USER MESSAGE ===\n"
        f"{user_msg}\n\n"
        f"Risk Tier: {tier} | Empathy Level: {empathy_level}/3\n\n"
        "Now respond naturally and helpfully. If they asked you to create something, actually create it!"
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,  # Slightly higher for more natural variation
    )

    text = resp.choices[0].message.content.strip()
    tags = render_citations(hits, allowed_tags)
    return text, tags