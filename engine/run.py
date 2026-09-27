"""
PidginBots engine entry point.
Reads config.json, hunts each product, scores leads, writes site/digest.json.
Deduplicates against engine/state.json so every run surfaces fresh signals only.

Run:  python3 engine/run.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hunt
import score
import digest as digest_mod

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(BASE, "engine", "state.json")


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def main():
    config = load_json(os.path.join(BASE, "config.json"), {"products": []})
    products = config.get("products", [])
    if not products:
        print("No products configured in config.json")
        return

    seen = load_json(STATE_FILE, {"urls": []})
    seen_set = set(seen["urls"])

    all_leads = []
    for product in products:
        pid = product.get("id") or product.get("name")
        candidates = hunt.hunt(product)
        fresh = 0
        for c in candidates:
            c["pid"] = pid
            c["pname"] = product.get("name", "")
            c["score"] = score.score_lead(c)
            c["heat"] = score.heat(c["score"])
            key = c["url"] + "|" + c["handle"]
            if key in seen_set or c["score"] < 35:
                continue
            seen_set.add(key)
            fresh += 1
            all_leads.append(c)
        print("Product '%s': %d candidates, %d fresh leads" % (product.get("name"), len(candidates), fresh))

    # persist dedup state (bounded)
    seen["urls"] = list(seen_set)[-5000:]
    with open(STATE_FILE, "w") as f:
        json.dump(seen, f)

    use_gemini = bool(os.environ.get("GEMINI_API_KEY"))
    d = digest_mod.build_digest(all_leads, products, use_gemini=use_gemini)
    payload = digest_mod.write_outputs(d, out_dir=os.path.join(BASE, "site"))
    print(digest_mod.console_summary(d))
    print("\nWrote %d leads to site/digest.json" % payload["lead_count"])


if __name__ == "__main__":
    main()
