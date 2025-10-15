#core/tone.py

def empathy_level(msg: str) -> int:
    m = msg.lower()
    score = 1
    if any(k in m for k in ["very anxious","panic","cry","shaking","can’t sleep","overwhelmed"]): score += 1
    if any(k in m for k in ["hopeless","worthless","numb"]): score += 1
    return min(score, 3)
