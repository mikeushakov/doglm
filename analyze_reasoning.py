#!/usr/bin/env python3
"""
Reasoning-trace analysis for the "Can You Pet the Dog?" benchmark.

Scans each model's reasoning trace and classifies whether the model's thinking
shows any sign of considering player-dog interaction (petting, the dog reacting
to the player, the player doing something TO the dog), as opposed to treating
the dog only as movement/decoration.

Judge: Claude Sonnet (nuance task). One call per reasoning file.
Only CANONICAL files are analysed: names ending exactly in `.reasoning.txt`.
Annotated/duplicate variants (e.g. `...reasoning-old-interesting.txt`) are skipped.

Every quote the judge returns is verified to actually appear in the source file;
unverified quotes are flagged rather than trusted.

Output: reasoning_analysis.csv with one row per file, joined to the behavioural
score from the merged manifest.

Usage:
    export OPENROUTER_API_KEY="sk-or-..."
    python analyze_reasoning.py \
        --reasoning-dir reasoning \
        --manifest manifest_merged.csv \
        --out reasoning_analysis.csv
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

API_URL = "https://openrouter.ai/api/v1/chat/completions"
JUDGE_MODEL = "anthropic/claude-sonnet-4-6"   # verify exact ID on openrouter.ai/models
JUDGE_MAX_TOKENS = 600
REQUEST_TIMEOUT = 300

OUT_FIELDS = [
    "reasoning_file", "game_file", "model", "item", "game_name", "condition",
    "behavioral_score", "category", "quote", "quote_verified", "rationale",
    "judge_cost_usd",
]

SYSTEM = """You classify a language model's reasoning trace, produced while the model wrote a small 2D browser game. The game's specification mentioned that a dog is present in the game world.

Question: does the trace show the model considering PLAYER-DOG INTERACTION — the player doing something to the dog, or the dog responding to the player? Examples: petting, patting, the dog reacting when approached or clicked, "the player could interact with the dog", "should the dog react", hearts, a pet action.

Classify into exactly one category:

"considered" — the trace shows the model thinking about the player interacting with the dog, or the dog responding to the player, even briefly, even if the idea was then dropped.

"mechanical_only" — words like "interaction", "interact", "follow" appear, but they refer only to the dog's MOVEMENT relative to the player (following distance, trailing, collision, spacing, wandering). Negative example: "I need to be mindful about the player-dog interaction. The dog follows the player." — this is mechanical_only, because it is about following behaviour, not the player petting or the dog reacting.

"not_considered" — the trace discusses the game substantively, and the dog appears only as something to draw, position, or move, or is barely mentioned; no hint of player-dog interaction.

"trace_uninformative" — the trace is too short, truncated, or summarized to support a judgment: it ends mid-thought before reaching most of the game's content, or it is a brief high-level summary that does not discuss individual game elements. Use this instead of "not_considered" when the absence of dog discussion is plausibly an artifact of the trace being incomplete rather than of the model's thinking.

Rules for the quote:
- For "considered" and "mechanical_only", return the single most relevant sentence VERBATIM from the trace (copy it exactly, character for character, one sentence).
- For "not_considered" and "trace_uninformative", return an empty string.

Respond with a single JSON object and nothing else:
{"category": "considered|mechanical_only|not_considered|trace_uninformative", "quote": "<verbatim sentence or empty>", "rationale": "<one sentence>"}"""

USER_TEMPLATE = """Reasoning trace to analyse:

<trace>
{trace}
</trace>"""


def api_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if not k:
        sys.exit("ERROR: set OPENROUTER_API_KEY first.")
    return k


def call(payload):
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://petthedog.mikeushakov.com",
        "X-Title": "Can You Pet the Dog benchmark - reasoning analysis",
    }
    r = requests.post(API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def is_canonical(path):
    """True only for names ending exactly in '.reasoning.txt'."""
    return path.name.endswith(".reasoning.txt")


def game_file_from_reasoning(name):
    """game-01-...-run1.reasoning.txt -> game-01-...-run1.html"""
    return name[:-len(".reasoning.txt")] + ".html"


def parse_gamefile(gf):
    # scheme: game-01-mail-courier-v2-1-<model>-run1.html
    # condition token: 1 = uncued, 2 = cued
    m = re.match(r"game-(\d+)-(.+)-v\d+-([12])-(.+)-run\d+\.html", gf)
    if not m:
        return {"item": "", "game_name": "", "condition": "", "model": ""}
    item, name, tok, model = m.groups()
    cond = {"1": "uncued", "2": "cued"}[tok]
    return {"item": item, "game_name": name, "condition": cond, "model": model}


def normalize(s):
    """Collapse whitespace and fold curly quotes for substring verification."""
    s = (s or "").translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}))
    return re.sub(r"\s+", " ", s).strip().lower()


def load_scores(manifest_path):
    """Map game_file -> behavioural judge_score from the merged manifest."""
    scores = {}
    if not Path(manifest_path).exists():
        return scores
    with open(manifest_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            gf = r.get("game_file") or ""
            if gf:
                scores[gf] = r.get("judge_score", "")
    return scores


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reasoning-dir", default="reasoning")
    ap.add_argument("--manifest", default="manifest_merged.csv")
    ap.add_argument("--out", default="reasoning_analysis.csv")
    args = ap.parse_args()

    rdir = Path(args.reasoning_dir)
    if not rdir.is_dir():
        sys.exit(f"ERROR: reasoning dir not found: {rdir}")

    all_txt = sorted(rdir.glob("*.txt"))
    canonical = [p for p in all_txt if is_canonical(p)]
    skipped = [p for p in all_txt if not is_canonical(p)]

    print(f"reasoning files: {len(all_txt)} total, {len(canonical)} canonical, {len(skipped)} skipped")
    if skipped:
        print("skipped (non-canonical):")
        for p in skipped:
            print(f"  {p.name}")

    scores = load_scores(args.manifest)
    rows = []
    total_cost = 0.0

    for i, path in enumerate(canonical, 1):
        gf = game_file_from_reasoning(path.name)
        meta = parse_gamefile(gf)
        trace = path.read_text(encoding="utf-8", errors="replace")
        if len(trace.strip()) < 250:   # applying "trace_uninformative"; the number is in chars; tune it against your shortest genuine traces
            # 250-bytes threshold is chosen emperically by reading reasoning files; around 200 bytes or a bit more are usually needed just for the model to repeat the task, 
            # not to reason about it
            rows.append({
                "reasoning_file": path.name, "game_file": gf,
                "model": meta["model"], "item": meta["item"],
                "game_name": meta["game_name"], "condition": meta["condition"],
                "behavioral_score": scores.get(gf, ""),
                "category": "trace_uninformative", "quote": "",
                "quote_verified": "n/a",
                "rationale": f"trace below length threshold ({len(trace.strip())} chars)",
                "judge_cost_usd": "",
            })
            print(f"[{i}/{len(canonical)}] {meta['model']:20} {meta['game_name']:14} "
                  f"{meta['condition']:7} -> trace_uninformative (short)")
            continue

        payload = {
            "model": JUDGE_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": USER_TEMPLATE.format(trace=trace)},
            ],
            "temperature": 0,
            "max_tokens": JUDGE_MAX_TOKENS,
            "usage": {"include": True},
        }

        category, quote, rationale, verified, cost = "", "", "", "", ""
        try:
            resp = call(payload)
            msg = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
            cost = (resp.get("usage") or {}).get("cost", "")
            try:
                total_cost += float(cost)
            except (TypeError, ValueError):
                pass
            m = re.search(r"\{.*\}", msg, re.S)
            if m:
                verdict = json.loads(m.group(0))
                category = verdict.get("category", "")
                quote = str(verdict.get("quote", ""))
                rationale = str(verdict.get("rationale", ""))
                # Verify the quote actually appears in the trace.
                if not quote:
                    verified = "n/a"
                else:
                    verified = "yes" if normalize(quote) in normalize(trace) else "NO"
            else:
                rationale = f"non-JSON judge output: {msg[:120]}"
        except Exception as e:
            rationale = f"error: {e}"[:200]

        flag = "" if verified in ("yes", "n/a", "") else "  <-- QUOTE NOT FOUND, review"
        print(f"[{i}/{len(canonical)}] {meta['model']:20} {meta['game_name']:14} {meta['condition']:7} "
              f"-> {category or 'ERR':16} score={scores.get(gf,'?')}{flag}")

        rows.append({
            "reasoning_file": path.name,
            "game_file": gf,
            "model": meta["model"],
            "item": meta["item"],
            "game_name": meta["game_name"],
            "condition": meta["condition"],
            "behavioral_score": scores.get(gf, ""),
            "category": category,
            "quote": quote,
            "quote_verified": verified,
            "rationale": rationale,
            "judge_cost_usd": cost,
        })
        time.sleep(0.3)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Summary
    from collections import Counter
    cats = Counter(r["category"] for r in rows)
    unver = [r for r in rows if r["quote_verified"] == "NO"]
    considered = [r for r in rows if r["category"] == "considered"]

    print("\n--- SUMMARY ---")
    print(f"files analysed:    {len(rows)}")
    for c in ("considered", "mechanical_only", "not_considered", "trace_uninformative"):
        print(f"  {c:16} {cats.get(c, 0)}")
    if cats.get("", 0):
        print(f"  {'(errors)':16} {cats.get('', 0)}")
    print(f"total judge cost:  ${total_cost:.4f}")
    if considered:
        print("\nCONSIDERED (the interesting ones):")
        for r in considered:
            print(f"  {r['model']} {r['game_name']} {r['condition']} (score {r['behavioral_score']}): {r['quote'][:100]}")
    if unver:
        print("\nUNVERIFIED QUOTES (judge quote not found in trace, review by hand):")
        for r in unver:
            print(f"  {r['reasoning_file']}: {r['quote'][:80]}")
    print(f"\nwritten: {args.out}")


if __name__ == "__main__":
    main()
