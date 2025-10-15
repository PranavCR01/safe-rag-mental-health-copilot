#core/safety.py

HELP = (
    "If you're in danger or thinking about harming yourself, please seek immediate help:\n"
    "• U.S.: 988 Suicide & Crisis Lifeline — call or text 988, or chat via 988lifeline.org\n"
    "• If outside the U.S., contact your local emergency number.\n"
    "• You can also reach a trusted person nearby right now."
)

def should_abstain(tier:int, had_evidence:bool) -> bool:
    if tier == 3: return True
    if not had_evidence: return True
    return False

def abstention_reply(tier:int):
    if tier == 3:
        return (
            "I'm really sorry you're feeling this way. I can't help with this here.\n\n"
            + HELP +
            "\n\nIf you'd like, I can stay while you contact support."
        )
    return ("I don't have enough reliable information to answer safely. "
            "Would you like general study-stress steps from WHO/CDC/APA instead?")

def red_flag(text:str) -> bool:
    # very conservative: if the model produced any risky phrases, re-abstain
    t = text.lower()
    return any(k in t for k in ["lethal","painless way","give you medication","diagnose you","dosage"])
