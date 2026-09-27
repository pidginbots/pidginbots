# PidginBots

An autonomous lead-finder. It scans public platforms for people asking for
what you sell, scores every lead on buying intent, and writes a daily digest
with a suggested opening message for each. Runs on free tiers. Total cost: $0.

## How it works

```
config.json  ->  engine/hunt.py   ->  engine/score.py  ->  engine/digest.py  ->  site/digest.json
(products)      (find signals)      (rank intent)        (openers, digest)     (site shows it)
```

1. **hunt** builds buying-intent queries from your product keywords and searches
   Hacker News (free), Reddit (free), and Google Programmable Search (100 free/day).
2. **score** ranks each candidate 0-98 on intent phrases, urgency, and recency.
   Hiring posts and sellers are pushed down.
3. **digest** writes `site/digest.json` with the top leads plus ready-to-send
   openers. If `GEMINI_API_KEY` is set, openers are written by Gemini (free tier);
   otherwise a clean template is used.

## Setup (all free)

1. Create an empty repo on GitHub, push this folder to it.
2. Enable the daily hunt: the included workflow `.github/daily-scan.yml`
   runs every morning at 07:00 Lagos time. Add repo secrets only if you want
   Google or Gemini (the engine works without them on HN + Reddit):
   - `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` — from programmablesearchengine.google.com (100 free searches/day)
   - `GEMINI_API_KEY` — from aistudio.google.com (free tier)
3. Deploy the site folder:
   - Netlify: drag the `site/` folder onto app.netlify.com/drop, or connect the repo for auto-deploy on every digest commit.
   - Surge: `npm i -g surge && surge site`
4. Edit `config.json` with your real products and keywords.

## Run locally

```
python3 engine/run.py
```

No dependencies required (standard library only). Output lands in
`site/digest.json` and prints to the console.

## Run a scan right now from the browser

GitHub repo -> Actions tab -> "PidginBots Daily Hunt" -> Run workflow.

## Notes

- Reddit blocks some datacenter IPs. If Reddit returns nothing, the engine
  skips it silently; HN and Google still work.
- The engine deduplicates against `engine/state.json`, so every daily digest
  contains only signals you have not seen before.
- Be a good citizen: the engine rate-limits itself and only reads public,
  official endpoints. No scraping behind logins, no spam. Openers are
  suggestions — the human sends them.
