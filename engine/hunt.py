"""
PidginBots hunt module.
Source connectors that scan public platforms for buying signals.
Each connector returns normalized lead candidates: dicts with keys
source, handle, text, url, date, keyword.
"""
import json
import os
import re
import time
import urllib.parse
import urllib.request

UA = "pidginbots-engine/1.0 (+https://pidginbots.example)"

import html as _html


def clean_text(raw):
    """Strip HTML tags and unescape entities so lead text reads like a human wrote it."""
    txt = _html.unescape(raw or "")
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt




def _get(url, headers=None, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


# ---------------------------------------------------------------- Hacker News
def search_hn(queries, max_per_query=15):
    """Free, no key. Comments are where people ask for recommendations."""
    out = []
    for q in queries:
        url = (
            "https://hn.algolia.com/api/v1/search?query="
            + urllib.parse.quote(q)
            + "&tags=comment&hitsPerPage=%d" % max_per_query
        )
        try:
            data = _get(url)
        except Exception:
            continue
        for hit in data.get("hits", []):
            text = hit.get("comment_text") or ""
            if not text:
                continue
            out.append({
                "source": "Hacker News",
                "handle": hit.get("author", "unknown"),
                "text": clean_text(text),
                "url": "https://news.ycombinator.com/item?id=%s" % hit.get("story_id", hit.get("objectID", "")),
                "date": (hit.get("created_at") or "")[:10],
                "keyword": q,
            })
        time.sleep(1.1)  # be a polite citizen
    return out


# ---------------------------------------------------------------- Reddit
def search_reddit(queries, max_per_query=20):
    """Public JSON endpoints. Datacenter IPs are often blocked; OAuth support
    can be added later via REDDIT_CLIENT_ID / REDDIT_SECRET in env."""
    out = []
    for q in queries:
        url = (
            "https://www.reddit.com/search.json?q="
            + urllib.parse.quote(q)
            + "&limit=%d&sort=new" % max_per_query
        )
        try:
            data = _get(url)
            children = data.get("data", {}).get("children", [])
        except Exception:
            continue  # blocked or rate-limited: skip silently
        for child in children:
            d = child.get("data", {})
            text = (d.get("selftext") or d.get("title") or "").strip()
            if not text:
                continue
            out.append({
                "source": "Reddit",
                "handle": d.get("author", "unknown"),
                "text": clean_text(text)[:1200],
                "url": "https://www.reddit.com" + (d.get("permalink") or ""),
                "date": time.strftime("%Y-%m-%d", time.gmtime(d.get("created_utc", 0))),
                "keyword": q,
            })
        time.sleep(1.2)
    return out


# ---------------------------------------------------------------- Google CSE
def search_google(queries, max_per_query=10):
    """Google Programmable Search. 100 free queries/day.
    Requires GOOGLE_API_KEY and GOOGLE_CSE_ID environment variables."""
    key = os.environ.get("GOOGLE_API_KEY")
    cse = os.environ.get("GOOGLE_CSE_ID")
    if not key or not cse:
        return []
    out = []
    for q in queries:
        url = (
            "https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&num=%d&q=%s"
            % (key, cse, max_per_query, urllib.parse.quote(q))
        )
        try:
            data = _get(url)
        except Exception:
            continue
        for item in data.get("items", []):
            out.append({
                "source": "Web",
                "handle": (item.get("displayLink") or "unknown").replace("www.", ""),
                "text": clean_text((item.get("title", "") + ". " + item.get("snippet", ""))),
                "url": item.get("link", ""),
                "date": "",
                "keyword": q,
            })
        time.sleep(0.6)
    return out


# ---------------------------------------------------------------- orchestrate
def hunt(product):
    """Run all enabled sources for one product. Returns candidate leads."""
    queries = build_queries(product)
    candidates = []
    sources = product.get("sources", ["hn", "reddit", "google"])
    if "hn" in sources:
        candidates += search_hn(queries)
    if "reddit" in sources:
        candidates += search_reddit(queries)
    if "google" in sources:
        candidates += search_google(queries)
    return candidates


def build_queries(product):
    """Turn product keywords into buying-intent search queries."""
    templates = [
        "looking for {k}",
        "anyone recommend {k}",
        "need {k} help",
        "which {k} is best",
        "{k} alternative",
        "tired of manual {k}",
    ]
    queries = []
    for kw in product.get("keywords", []):
        for t in templates:
            queries.append(t.format(k=kw))
    return queries[:12]  # stay inside free-tier budgets
