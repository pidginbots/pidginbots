"""
PidginBots digest module.
Builds the daily digest: ranked leads with suggested opening messages.
Openers are template-generated offline; if a GEMINI_API_KEY is present the
engine optionally polishes them (free tier). Falls back gracefully.
"""
import json
import os
import urllib.parse
import urllib.request


def template_opener(lead, product):
    first = (lead.get("handle") or "there").split()[0]
    kw = lead.get("keyword", "this")
    return (
        "Hi %s — saw your post about %s. %s "
        "If it helps, I can show you how it works in two minutes. No pressure at all."
        % (first, kw, product.get("pitch", ""))
    )


def gemini_opener(lead, product):
    """Optional: use Google Gemini free tier to write a sharper opener."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    prompt = (
        "Write a short, warm, non-spammy opening message (max 3 sentences) to a person "
        "who posted this: '%s' — recommending this product: '%s'. "
        "No emojis, no hashtags, sound like a human, mention the exact problem they described."
        % (lead.get("text", "")[:400], product.get("name", "") + " — " + product.get("pitch", ""))
    )
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + key,
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode())
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return text if text else None
    except Exception:
        return None


def build_digest(leads, products, use_gemini=False):
    """leads: scored lead dicts; products: list of product dicts."""
    by_id = {p["id"]: p for p in products}
    digest = []
    for lead in sorted(leads, key=lambda l: l["score"], reverse=True)[:20]:
        product = by_id.get(lead["pid"], {})
        opener = (gemini_opener(lead, product) if use_gemini else None) or template_opener(lead, product)
        digest.append({**lead, "opener": opener})
    return digest


def write_outputs(digest, out_dir="site"):
    os.makedirs(out_dir, exist_ok=True)
    payload = {
        "generated": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        "lead_count": len(digest),
        "leads": digest,
    }
    with open(os.path.join(out_dir, "digest.json"), "w") as f:
        json.dump(payload, f, indent=2)
    return payload


def console_summary(digest):
    lines = ["", "PIDGINBOTS DAILY DIGEST", "=" * 60]
    for i, lead in enumerate(digest[:10], 1):
        lines.append(
            "%d. [%s %d] %s (%s) — %s" % (i, lead["heat"], lead["score"], lead["handle"], lead["source"], lead["url"])
        )
        lines.append("   " + lead["text"][:140].replace("\n", " "))
        lines.append("   OPENER: " + lead["opener"][:140])
    lines.append("=" * 60)
    return "\n".join(lines)
