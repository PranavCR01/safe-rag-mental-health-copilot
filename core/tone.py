#core/tone.py

from typing import Dict, List


def _lower(s: str) -> str:
    return (s or "").lower()


def analyze_tone_and_cues(msg: str) -> Dict:
    """
    Analyze the user message for emotional cues and return:
      - empathy_level: 1 (low) to 3 (high)
      - cues: list of strings describing detected cues
      - template: which response template to prefer
                  ("panic" | "sleep" | "self_talk" | "generic")

    Rule-based, fully explainable.
    """
    m = _lower(msg)
    cues: List[str] = []
    empathy = 1

    # ---- Cue buckets ----

    # Panic / overwhelm / acute stress
    panic_terms = [
        "panic", "panicking", "panic attack",
        "overwhelmed", "overwhelming",
        "shaking", "heart is racing",
        "can't breathe", "cannot breathe",
        "freaking out", "losing my mind", "lose my mind",
        "breakdown", "meltdown",
    ]
    if any(t in m for t in panic_terms):
        cues.append("panic/overwhelm")
        empathy = max(empathy, 3)

    # Sleep / exhaustion / insomnia
    sleep_terms = [
        "can't sleep", "cannot sleep", "insomnia",
        "haven't slept", "no sleep",
        "stayed up all night", "awake all night",
        "exhausted", "drained",
    ]
    if any(t in m for t in sleep_terms):
        cues.append("sleep/insomnia")
        empathy = max(empathy, 2)

    # Negative self-talk / low self-worth
    self_talk_terms = [
        "hopeless", "worthless", "numb",
        "i'm a failure", "im a failure",
        "i am a failure",
        "i'm so dumb", "im so dumb",
        "i'm stupid", "im stupid",
        "i hate myself",
    ]
    if any(t in m for t in self_talk_terms):
        cues.append("negative_self_talk")
        empathy = max(empathy, 3)

    # General exam anxiety (milder but relevant)
    exam_terms = [
        "exam", "finals", "midterm", "test",
        "grade", "gpa",
        "study stress", "too much to study",
        "so much to study",
        "failed before", "failed last time",
    ]
    if any(t in m for t in exam_terms):
        cues.append("exam_stress")
        empathy = max(empathy, 2)

    # If no strong cues at all but message is clearly stressy
    generic_stress_terms = [
        "stressed", "anxious", "anxiety",
        "nervous", "worried", "worrying",
    ]
    if not cues and any(t in m for t in generic_stress_terms):
        cues.append("general_stress")
        empathy = max(empathy, 2)

    # ---- Choose template based on strongest cue family ----
    # Priority order: panic > sleep > negative self-talk > generic
    template = "generic"
    if any("panic" in c for c in cues):
        template = "panic"
    elif any("sleep" in c for c in cues):
        template = "sleep"
    elif any("negative_self_talk" in c for c in cues):
        template = "self_talk"
    else:
        template = "generic"

    # Clamp empathy within [1, 3]
    empathy = min(max(empathy, 1), 3)

    return {
        "empathy_level": empathy,
        "cues": cues,
        "template": template,
    }


def empathy_level(msg: str) -> int:
    """
    Backwards-compatible helper used by the rest of the app.
    Internally calls analyze_tone_and_cues and just returns empathy_level.
    """
    analysis = analyze_tone_and_cues(msg)
    return analysis["empathy_level"]


# ====== Template selection & tone block for the LLM ======

def choose_template(cues: List[str], empathy_level: int) -> str:
    """
    Small helper so we can override / tweak template choice if needed.
    Currently just mirrors the logic in analyze_tone_and_cues.
    """
    if any("panic" in c for c in cues):
        return "panic"
    if any("sleep" in c for c in cues):
        return "sleep"
    if any("negative_self_talk" in c for c in cues):
        return "self_talk"
    return "generic"


def build_tone_block(tone: Dict) -> str:
    """
    Turn the tone analysis into a short hint block we inject into the prompt.
    """
    emp = tone.get("empathy_level", 1)
    cues = tone.get("cues") or []
    template_name = tone.get("template") or choose_template(cues, emp)

    cues_str = ", ".join(cues) if cues else "none"

    tone_block = (
        "TONE SIGNALS:\n"
        f"- EmpathyLevelHint: {emp} (1=low, 3=high)\n"
        f"- Cues: {cues_str}\n"
        f"- TemplateHint: {template_name}\n"
        "Use this to adjust warmth and focus while still following the "
        "Acknowledge → Explain → Act structure."
    )
    return tone_block


# ====== Too-formal / clinical detector ======

def is_too_formal(text: str) -> bool:
    """
    Heuristic detector for replies that sound too formal / clinical.
    Not for safety, just style quality.
    """
    t = _lower(text)

    formal_markers = [
        "in conclusion",
        "furthermore",
        "moreover",
        "in addition",
        "it is recommended that",
        "it is important to note",
        "the patient",
        "symptoms include",
        "treatment plan",
        "clinical",
        "diagnosis",
        "presenting with",
        "coping mechanisms such as",
    ]

    hits = sum(1 for p in formal_markers if p in t)

    has_contraction = any(
        c in t
        for c in [
            "n't",
            "’re",
            "I'm",
            "i'm",
            "you're",
            "you’re",
            "it's",
            "it’s",
            "don't",
            "don’t",
            "can't",
            "can’t",
        ]
    )

    if hits >= 2:
        return True
    if hits >= 1 and not has_contraction:
        return True

    return False
