"""
PidginBots scoring module.
Scores candidate leads on buying intent, urgency and recency.
Score range 0-98. 80+ = HOT, 50-79 = WARM, below = COOL.
"""
import re
import datetime

INTENT_PATTERNS = [
    (r"\blooking for\b", 16),
    (r"\banyone (know|recommend|suggest)", 16),
    (r"\bplease (who|anyone|any)", 15),
    (r"\bwhere (can|do) i (get|buy|find)", 14),
    (r"\bwhat do you (use|recommend)", 13),
    (r"\bneed (a|an|some|help)", 12),
    (r"\bcan anyone (help|point)", 10),
    (r"\bhow do (i|you) (get|find|choose)", 9),
    (r"\bsuggest(ions?)?\b", 8),
    (r"\b(honest )?review(s)?\b", 7),
    (r"\b(tired|sick|fed up)\b", 9),
    (r"\bready to (switch|buy|pay)", 18),
    (r"\b(recommendation|recommendations)\b", 12),
]

URGENCY_PATTERNS = [
    (r"\b(urgent|urgently|asap|immediately)\b", 12),
    (r"\b(today|tonight|this week|right now)\b", 8),
    (r"\bby (next|tomorrow|monday|friday)\b", 6),
    (r"\b(deadline|running out)\b", 6),
]

NEGATIVE_PATTERNS = [
    (r"\b(i am|we are|are you) hiring\b", -25),   # recruiting, not buying
    (r"\b(job|vacancy|open role)s?\b", -18),
    (r"\b(for sale|selling my|ad)\b", -10),      # seller, not buyer
]


def score_lead(candidate):
    text = " " + (candidate.get("text") or "").lower() + " "
    score = 30  # baseline: surfaced by a buying-intent query at all
    for pattern, weight in INTENT_PATTERNS:
        if re.search(pattern, text):
            score += weight
    for pattern, weight in URGENCY_PATTERNS:
        if re.search(pattern, text):
            score += weight
    for pattern, weight in NEGATIVE_PATTERNS:
        if re.search(pattern, text):
            score += weight
    if "?" in (candidate.get("text") or ""):
        score += 4

    # the queried keyword must actually appear in the post, else heavy penalty
    kw = (candidate.get("keyword") or "").lower().strip()
    if kw:
        kw_core = kw.replace("looking for", "").replace("anyone recommend", "").strip()
        kw_words = [w for w in kw_core.split() if len(w) > 2]
        # full phrase match first, else ALL significant words must appear
        if kw_core and kw_core in text:
            score += 12  # exact phrase: strongest possible signal
            hit = True
        else:
            hit = all(w in text for w in kw_words) if kw_words else True
        if not hit:
            score -= 45
    if candidate.get("source") == "Hacker News":
        score += 3  # comment threads skew toward genuine requests
    # recency bonus
    date = candidate.get("date") or ""
    try:
        d = datetime.date.fromisoformat(date[:10])
        age = (datetime.date.today() - d).days
        if age <= 1:
            score += 8
        elif age <= 3:
            score += 5
        elif age <= 7:
            score += 3
        elif age > 30:
            score -= 8
    except ValueError:
        pass
    return max(0, min(98, score))


def heat(score):
    if score >= 80:
        return "HOT"
    if score >= 50:
        return "WARM"
    return "COOL"
