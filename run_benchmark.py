#!/usr/bin/env python3
"""
Can You Pet the Dog? - benchmark runner (MVP)

Generates games from PRDs via OpenRouter, then scores each game with an
LLM judge. Writes game files, optional reasoning dumps, and a manifest CSV.

Usage:
    export OPENROUTER_API_KEY="sk-or-..."
    python run_benchmark.py --model deepseek/deepseek-chat --runs 1
    python run_benchmark.py --model deepseek/deepseek-chat --runs 1 --prds PRD-01-mail-courier-v1-uncued.md
    python run_benchmark.py --model deepseek/deepseek-chat --judge-only
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

API_URL = "https://openrouter.ai/api/v1/chat/completions"

PRD_DIR = Path("prds")
GAME_DIR = Path("games")
REASONING_DIR = Path("reasoning")
MANIFEST = Path("manifest.csv")

# Judge model. Verify the exact ID on https://openrouter.ai/models before running.
JUDGE_MODEL = "mistralai/mistral-medium-3"

TEMPERATURE = 1.0
MAX_TOKENS = 32000
JUDGE_MAX_TOKENS = 2000
REQUEST_TIMEOUT = 900  # seconds
RETRY_ON_FAILURE = 1   # one retry per generation, per the pre-registered rule

MANIFEST_FIELDS = [
    "timestamp", "model", "item", "game_name", "prd_version", "condition", "run",
    "prd_file", "game_file", "finish_reason", "prompt_tokens", "completion_tokens",
    "reasoning_tokens", "total_tokens", "cost_usd", "latency_s", "temperature",
    "fences_stripped", "attempt", "generation_ok", "note",
    "syntax_ok", "judge_model", "judge_score", "judge_evidence", "judge_cost_usd",
]

# Value written to judge_score when the game's JavaScript fails to parse.
# Non-numeric outcome labels written to judge_score. These are states, not scores:
# the game yields no valid observation, so it is excluded from the 0-to-10 total.
FAILED_LABEL = "FAILED"   # game does not parse / is truncated / cannot be checked
NO_DOG_LABEL = "NO_DOG"   # game runs but contains no dog at all

# ---------------------------------------------------------------------------
# JUDGE PROMPT  (mirrors the manual scoring protocol on the benchmark page)
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """You are scoring a browser game's source code. Read the code and report whether the player can interact with the dog that appears in the game, using exactly this scale:

2 = PETTING. A deliberate player action aimed at the dog (a keypress while positioned near the dog, or a mouse click on the dog) that reads as petting or affection, and produces a dog-specific response: a petting animation, hearts, a message such as "You pet the dog", a happy reaction or tail wag triggered by that action. The action must be affectionate toward the dog, not a command that merely uses the dog. Mechanical contact between the player and the dog alone, without a deliberate player-triggered petting action, can never score 2, even if the code calls the mechanic petting. Score 2 requires a separate deliberate petting action by the player.

1 = OTHER DOG RESPONSE. Something the player does causes a dog-specific response, but the interaction is not petting. This includes the dog reacting when the player approaches or touches it, or responding to a player command such as a whistle or call. Dog behavior caused only by a timer, randomness, or the normal game loop does not count and scores 0.

0 = INERT DOG. The dog exists and may move or follow the player, but nothing the player does produces a dog-specific behavioral reaction. The following are all INERT and score 0:
- Cosmetic animation that runs continuously regardless of the player (an always-wagging tail, a bobbing idle animation).
- Pure collision physics: the dog being displaced, pushed, bounced away, or blocked when the player touches it, when this is only position/velocity resolution with no accompanying expressive or behavioral response (no bark, no visual reaction, no state change beyond position).
- The dog merely following the player.
- Generic feedback that fires regardless of the dog (an interact key that prints "Move closer to a marked house" when pressed anywhere).

NO_DOG = the code contains no dog at all: no dog object, no dog drawing, no reference to a dog anywhere. This is a distinct outcome, not a low score.

Additional rules:
- A dog whistle or call the player triggers deliberately counts as 1 (a command response), not 2, because it is not affection.
- The response must be attached to the dog specifically, in the code.
- Score what the code actually wires up: a function named petDog that is never reachable from any input handler or game loop does not count.

Respond with a single JSON object and nothing else. The score must be one of "NO_DOG", 0, 1, 2:
{"score": 0, "evidence": "<the exact code lines or function names that justify the score, or 'no dog present in code' / 'no dog interaction found in input handling' as appropriate>", "reasoning": "<one or two sentences>"}"""

JUDGE_USER_TEMPLATE = """Score this game's source code.

```html
{code}
```"""


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("ERROR: set OPENROUTER_API_KEY in your environment first.")
    return key


def parse_prd_filename(name):
    """PRD-01-mail-courier-v2-1.md -> (01, mail-courier, v2, uncued)
    Condition token: 1 = uncued, 2 = cued."""
    m = re.match(r"PRD-(\d+)-(.+)-(v\d+)-([12])\.md$", name)
    if not m:
        return None
    condition = {"1": "uncued", "2": "cued"}[m.group(4)]
    return m.group(1), m.group(2), m.group(3), condition
    

def model_slug(model_id):
    """anthropic/claude-fable-5 -> claude-fable-5"""
    return model_id.split("/")[-1].lower().replace(".", "-")


# Model-blind condition tokens used in the SAVED game filename, so a model
# cannot read its experimental condition from the output-filename instruction.
# uncued -> "1", cued -> "2".  Example: game-01-mail-courier-v2-2-<model>-run1.html
CONDITION_TOKEN = {"uncued": "1", "cued": "2"}


def game_filename(item, game_name, version, condition, model, run):
    tok = CONDITION_TOKEN.get(condition, condition)
    return f"game-{item}-{game_name}-{version}-{tok}-{model_slug(model)}-run{run}.html"


def strip_fences(text):
    """Remove ```html ... ``` wrappers if the model added them. Returns (code, stripped?)."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
        t = re.sub(r"\n```\s*$", "", t)
        return t.strip(), True
    return t, False


def call_openrouter(payload, max_retries=4):
    """One API call with backoff on rate limits (429) and transient 5xx.
    Returns (response_json, latency_seconds)."""
    headers = {
        "Authorization": f"Bearer {api_key()}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://petthedog.mikeushakov.com",
        "X-Title": "Can You Pet the Dog benchmark",
    }
    t0 = time.time()
    backoff = 5
    for attempt in range(max_retries + 1):
        r = requests.post(API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        if r.status_code == 200:
            return r.json(), round(time.time() - t0, 1)
        # Rate limited or transient server error: wait and retry.
        if r.status_code in (429, 500, 502, 503, 529) and attempt < max_retries:
            wait = backoff
            ra = r.headers.get("Retry-After")
            if ra:
                try:
                    wait = max(wait, int(float(ra)))
                except ValueError:
                    pass
            time.sleep(wait)
            backoff = min(backoff * 2, 60)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:400]}")
    raise RuntimeError("exhausted retries")


def usage_fields(resp):
    """Pull token counts and cost out of an OpenRouter response."""
    u = resp.get("usage") or {}
    details = u.get("completion_tokens_details") or {}
    return {
        "prompt_tokens": u.get("prompt_tokens", ""),
        "completion_tokens": u.get("completion_tokens", ""),
        "reasoning_tokens": details.get("reasoning_tokens", ""),
        "total_tokens": u.get("total_tokens", ""),
        "cost_usd": u.get("cost", ""),
    }


def message_of(resp):
    return (resp.get("choices") or [{}])[0].get("message") or {}


def finish_reason_of(resp):
    return (resp.get("choices") or [{}])[0].get("finish_reason", "")


# ---------------------------------------------------------------------------
# GENERATION
# ---------------------------------------------------------------------------

def generate_one(model, prd_path, run, temperature):
    """Generate one game. Returns a manifest row dict."""
    parsed = parse_prd_filename(prd_path.name)
    if not parsed:
        print(f"  SKIP (filename not in expected format): {prd_path.name}")
        return None
    item, game_name, version, condition = parsed

    prd_text = prd_path.read_text(encoding="utf-8")
    game_file = GAME_DIR / game_filename(item, game_name, version, condition, model, run)

    row = {f: "" for f in MANIFEST_FIELDS}
    row.update({
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model, "item": item, "game_name": game_name,
        "prd_version": version, "condition": condition, "run": run,
        "prd_file": prd_path.name, "game_file": game_file.name,
        "temperature": temperature,
    })

    for attempt in range(1, RETRY_ON_FAILURE + 2):
        row["attempt"] = attempt
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prd_text}],
            "temperature": temperature,
            "max_tokens": MAX_TOKENS,
            "usage": {"include": True},
        }
        try:
            resp, latency = call_openrouter(payload)
        except Exception as e:
            row["note"] = f"api error: {e}"[:300]
            row["generation_ok"] = "no"
            print(f"  ERROR {prd_path.name} run{run} attempt{attempt}: {e}")
            time.sleep(3)
            continue

        msg = message_of(resp)
        raw = msg.get("content") or ""
        reasoning = msg.get("reasoning") or ""
        fr = finish_reason_of(resp)

        row.update(usage_fields(resp))
        row["latency_s"] = latency
        row["finish_reason"] = fr

        code, stripped = strip_fences(raw)
        row["fences_stripped"] = "yes" if stripped else "no"

        # Sanity checks: truncated output, or not a game at all.
        broken = (fr == "length") or ("<canvas" not in code.lower())
        if broken:
            row["note"] = f"suspect output (finish_reason={fr}, canvas={'<canvas' in code.lower()})"
            row["generation_ok"] = "no"
            print(f"  SUSPECT {prd_path.name} run{run} attempt{attempt}: {row['note']}")
            if attempt <= RETRY_ON_FAILURE:
                continue

        game_file.write_text(code, encoding="utf-8")
        row["generation_ok"] = "no" if broken else "yes"
        if not broken:
            row["note"] = ""

        if reasoning:
            REASONING_DIR.mkdir(exist_ok=True)
            (REASONING_DIR / (game_file.stem + ".reasoning.txt")).write_text(reasoning, encoding="utf-8")

        print(f"  OK {game_file.name}  ({row['completion_tokens']} out tok, ${row['cost_usd']}, {latency}s)")
        return row

    return row


# ---------------------------------------------------------------------------
# SYNTAX CHECK (Tier 1: does the game's JavaScript parse?)
# ---------------------------------------------------------------------------

_NODE = shutil.which("node")


def node_available():
    return _NODE is not None


def extract_script_js(html):
    """
    Return the JavaScript from the HTML's <script> block(s).

    Handles three real-world messes seen in generated files:
    - leftover markdown fences (```html ... ```) anywhere in the file
    - conversational preamble before the actual HTML
    - a <script> that is never closed because the generation was truncated
      (take everything after the opening tag, matching a permissive extractor)

    Returns (js: str, closed: bool). `closed` is False when an opening <script>
    had no matching </script>, which signals a truncated file.
    """
    # Drop markdown fences so they can't leak into the JS.
    cleaned = re.sub(r"```[a-zA-Z]*", "", html)

    # Normal case: one or more properly closed <script>...</script> blocks.
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", cleaned, re.S | re.I)
    if blocks:
        return "\n".join(blocks).strip(), True

    # Truncated case: an opening <script ...> with no closing tag.
    m = re.search(r"<script[^>]*>(.*)$", cleaned, re.S | re.I)
    if m:
        return m.group(1).strip(), False

    return "", True


def syntax_check(game_file):
    """
    Tier-1 check: extract the game's JavaScript and run `node --check` on it.
    Returns (ok: bool|None, message: str).
    ok = True  -> parses cleanly
    ok = False -> parse error (message holds the first error line)
    ok = None  -> could not check (node missing, empty file, no script block)
    """
    if not node_available():
        return None, "node not installed; syntax check skipped"

    try:
        html = game_file.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"could not read file: {e}"

    if not html.strip():
        return False, "empty file"

    js, closed = extract_script_js(html)
    if not js:
        return None, "no <script> block found"
    if not closed:
        # Opening <script> with no closing tag: the file was cut off.
        # Still run node on what we have; if it parses, it is genuinely just
        # missing the closing tag, but usually truncation also breaks the JS.
        pass

    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(js)
        tmp_path = tf.name
    try:
        proc = subprocess.run(
            [_NODE, "--check", tmp_path],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        os.unlink(tmp_path)
        return None, f"node check failed to run: {e}"
    os.unlink(tmp_path)

    if proc.returncode == 0:
        if not closed:
            return False, "truncated file: <script> never closed"
        return True, ""
    # Node prints the offending source line, then a caret line, then the error.
    # Grab the SyntaxError line if present, else the first stderr line.
    err_lines = [ln.strip() for ln in proc.stderr.splitlines() if ln.strip()]
    msg = ""
    for ln in err_lines:
        if "Error:" in ln:
            msg = ln
            break
    if not msg and err_lines:
        msg = err_lines[0]
    msg = re.sub(r"^.*\.js:?", "", msg).strip()
    return False, (msg or "parse error")[:200]


# ---------------------------------------------------------------------------
# JUDGING
# ---------------------------------------------------------------------------

def judge_one(game_file):
    """Score one game file. Returns (score, evidence, cost)."""
    code = game_file.read_text(encoding="utf-8")
    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": JUDGE_USER_TEMPLATE.format(code=code)},
        ],
        "temperature": 0,
        "max_tokens": JUDGE_MAX_TOKENS,
        "usage": {"include": True},
    }
    try:
        resp, _ = call_openrouter(payload)
    except Exception as e:
        return "", f"judge api error: {e}"[:200], ""

    text = (message_of(resp).get("content") or "").strip()
    cost = usage_fields(resp)["cost_usd"]

    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return "", f"judge returned non-JSON: {text[:150]}", cost
    try:
        verdict = json.loads(m.group(0))
    except json.JSONDecodeError:
        return "", f"judge JSON parse failed: {text[:150]}", cost

    score = verdict.get("score", "")
    evidence = str(verdict.get("evidence", ""))[:400]
    # The judge emits -1 for "no dog present"; store it as a plain state label
    # so nothing downstream mistakes it for a numeric score point.
    if str(score).strip().upper() in ("-1", "NO_DOG"):
        score = NO_DOG_LABEL
    return score, evidence, cost


# ---------------------------------------------------------------------------
# WORKER (one full job: generate + syntax-gate + judge)
# ---------------------------------------------------------------------------

def process_job(model, prd_path, run, temperature, do_judge):
    """Generate one game and (optionally) score it. Returns a manifest row dict.
    Safe to call from multiple threads: touches only its own files and the
    shared GAME_DIR (distinct filenames per job)."""
    row = generate_one(model, prd_path, run, temperature)
    if not row:
        return None
    if do_judge and row.get("generation_ok") == "yes":
        gf = GAME_DIR / row["game_file"]
        syn_ok, syn_msg = syntax_check(gf)
        if syn_ok is False:
            row["syntax_ok"] = "no"
            row["judge_model"] = JUDGE_MODEL
            row["judge_score"] = FAILED_LABEL
            row["judge_evidence"] = f"syntax error: {syn_msg}"
            row["judge_cost_usd"] = ""
        elif syn_ok is None and node_available():
            row["syntax_ok"] = "review"
            row["judge_model"] = JUDGE_MODEL
            row["judge_score"] = FAILED_LABEL
            row["judge_evidence"] = f"could not check: {syn_msg}"
            row["judge_cost_usd"] = ""
        else:
            row["syntax_ok"] = "yes" if syn_ok else ""
            score, evidence, jcost = judge_one(gf)
            row["judge_model"] = JUDGE_MODEL
            row["judge_score"] = score
            row["judge_evidence"] = evidence
            row["judge_cost_usd"] = jcost
    return row


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, nargs="+",
                    help="one or more OpenRouter model ids, e.g. deepseek/deepseek-chat mistralai/mistral-medium-3")
    ap.add_argument("--runs", type=int, default=1, help="generations per PRD")
    ap.add_argument("--prds", nargs="*", help="specific PRD filenames (default: all in prds/)")
    ap.add_argument("--temperature", type=float, default=TEMPERATURE)
    ap.add_argument("--workers", type=int, default=4,
                    help="parallel requests in flight (start low, 4-6, to respect rate limits)")
    ap.add_argument("--no-judge", action="store_true", help="generate only, skip scoring")
    ap.add_argument("--judge-only", action="store_true", help="score existing games, no generation")
    args = ap.parse_args()

    GAME_DIR.mkdir(exist_ok=True)

    models = args.model
    rows = []
    rows_lock = threading.Lock()

    if not node_available():
        print("WARNING: Node.js not found; syntax_ok will be blank and no game will be marked FAILED for syntax.")

    if args.judge_only:
        # Judge existing games for each model, in parallel.
        jobs = []
        for model in models:
            pattern = f"game-*-{model_slug(model)}-run*.html"
            for gf in sorted(GAME_DIR.glob(pattern)):
                jobs.append((model, gf))
        print(f"Judging {len(jobs)} existing game(s) across {len(models)} model(s), {args.workers} workers")

        def judge_job(model, gf):
            syn_ok, syn_msg = syntax_check(gf)
            
            match = re.match(
                rf"^game-(\d+)-(.+)-(v\d+)-([12])-"
                rf"{re.escape(model_slug(model))}-run(\d+)\.html$",
                gf.name,
            )

            if not match:
                raise ValueError(f"Could not parse game filename: {gf.name}")

            item, game_name, version, condition_token, run = match.groups()

            row = {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "model": model,
                "item": item,
                "game_name": game_name,
                "prd_version": version,
                "condition": {"1": "uncued", "2": "cued"}[condition_token],
                "run": int(run),
                "prd_file": f"PRD-{item}-{game_name}-{version}-{condition_token}.md",
                "game_file": gf.name,
                "judge_model": JUDGE_MODEL,
            }
            if syn_ok is False:
                row.update({"syntax_ok": "no", "judge_score": FAILED_LABEL,
                            "judge_evidence": f"syntax error: {syn_msg}", "judge_cost_usd": ""})
                print(f"  FAILED {gf.name} :{syn_msg}")
            elif syn_ok is None and node_available():
                row.update({"syntax_ok": "review", "judge_score": FAILED_LABEL,
                            "judge_evidence": f"could not check: {syn_msg}", "judge_cost_usd": ""})
                print(f"  REVIEW {gf.name} :{syn_msg}")
            else:
                score, evidence, cost = judge_one(gf)
                row.update({"syntax_ok": "yes" if syn_ok else "", "judge_score": score,
                            "judge_evidence": evidence, "judge_cost_usd": cost})
                print(f"  JUDGE {gf.name} -> {score}")
            return row

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = [ex.submit(judge_job, m, gf) for m, gf in jobs]
            for fut in as_completed(futs):
                r = fut.result()
                if r:
                    with rows_lock:
                        rows.append(r)
    else:
        if args.prds:
            prds = [PRD_DIR / p for p in args.prds]
        else:
            prds = sorted(PRD_DIR.glob("PRD-*.md"))
        missing = [p for p in prds if not p.exists()]
        if missing:
            sys.exit(f"ERROR: PRD file(s) not found: {', '.join(str(p) for p in missing)}")
        if not prds:
            sys.exit(f"ERROR: no PRD files found in {PRD_DIR}/")

        # Build the full job list: every model x PRD x run.
        jobs = [(model, prd, run)
                for model in models
                for run in range(1, args.runs + 1)
                for prd in prds]
        print(f"Generating {len(jobs)} game(s): {len(models)} model(s) x {len(prds)} PRDs x {args.runs} run(s), "
              f"{args.workers} workers, temp={args.temperature}")

        done = 0
        total = len(jobs)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(process_job, m, prd, run, args.temperature, not args.no_judge): (m, prd, run)
                    for (m, prd, run) in jobs}
            for fut in as_completed(futs):
                m, prd, run = futs[fut]
                done += 1
                try:
                    r = fut.result()
                except Exception as e:
                    print(f"  [{done}/{total}] ERROR {m} {prd.name}: {e}")
                    continue
                if not r:
                    continue
                sc = r.get("judge_score", "")
                print(f"  [{done}/{total}] {model_slug(m):22} {prd.name:34} -> {sc}")
                with rows_lock:
                    rows.append(r)

    # Append to manifest
    write_header = not MANIFEST.exists()
    with MANIFEST.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in MANIFEST_FIELDS})

    # Summary
    def num(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return 0.0

    gen_cost = sum(num(r.get("cost_usd")) for r in rows)
    judge_cost = sum(num(r.get("judge_cost_usd")) for r in rows)
    out_tok = sum(num(r.get("completion_tokens")) for r in rows)
    reas_tok = sum(num(r.get("reasoning_tokens")) for r in rows)
    ok = sum(1 for r in rows if r.get("generation_ok") == "yes")
    failed = sum(1 for r in rows if r.get("generation_ok") == "no")
    scores = [num(r["judge_score"]) for r in rows
              if str(r.get("judge_score")) not in ("", NO_DOG_LABEL, FAILED_LABEL)]
    excluded = sum(1 for r in rows if str(r.get("judge_score")) == NO_DOG_LABEL)
    broken = sum(1 for r in rows if str(r.get("judge_score")) == FAILED_LABEL)

    print("\n--- SUMMARY ---")
    print(f"models:            {', '.join(models)}")
    print(f"games generated:   {ok} ok, {failed} failed")
    print(f"output tokens:     {out_tok:.0f}  (of which reasoning: {reas_tok:.0f})")
    print(f"generation cost:   ${gen_cost:.4f}")
    print(f"judging cost:      ${judge_cost:.4f}")
    print(f"total cost:        ${gen_cost + judge_cost:.4f}")
    if scores:
        print(f"judge scores:      {[int(s) for s in scores]}  (sum {sum(scores):.0f} of {len(scores) * 2})")

    if excluded:
        print(f"NO_DOG (excluded): {excluded}")

    if broken:
        print(f"FAILED (excluded): {broken}")

    positive = [
        r for r in rows
        if str(r.get("judge_score")) in ("1", "2")
    ]

    if positive:
        print(f"\n--- POSITIVE SCORES ({len(positive)}) ---")
        for r in sorted(
            positive,
            key=lambda x: (
                -int(x["judge_score"]),
                x["model"],
                x["game_name"],
            ),
        ):
            print(
                f"  score={r['judge_score']}  "
                f"{r['model']:40} {r['game_name']:16} "
                f"{r['condition']:7} run{r['run']}"
            )

    print(f"manifest:          {MANIFEST}")


if __name__ == "__main__":
    main()
