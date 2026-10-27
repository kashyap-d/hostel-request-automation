"""Run the classifier against hand-labelled complaints and report how well it does.

Usage:
    python -m evals.run_eval                       # default model
    python -m evals.run_eval --model llama-3.3-70b-versatile
    python -m evals.run_eval --limit 10            # quick smoke run

Needs GROQ_API_KEY. Writes a markdown report to evals/results/.
"""

import argparse
import json
import re
import statistics
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from classifier import DEFAULT_MODEL, classify_complaint, make_llm

EVAL_DIR = Path(__file__).parent
CASES_FILE = EVAL_DIR / "complaints.jsonl"
RESULTS_DIR = EVAL_DIR / "results"

LOCATION_STOPWORDS = {"the", "of", "in", "at", "near", "outside", "on", "a", "an", "and"}


def load_cases(path=CASES_FILE):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def accepts(expected, actual) -> bool:
    """Expected may be one value or a list of acceptable values."""
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


def location_tokens(text):
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in LOCATION_STOPWORDS}


def location_matches(expected, actual) -> bool:
    """
    None expected means the message gives no location, so the model must not invent one.
    Otherwise every meaningful word of the expected location must appear in the prediction,
    so "B block, room 214" matches "room 214, B block".
    """
    if expected is None:
        return actual is None or actual.strip() == ""
    if not actual:
        return False
    return location_tokens(expected) <= location_tokens(actual)


def score_case(case, ticket):
    """Compare one prediction with its labels. Returns {check_name: passed} for applicable checks."""
    expected = case["expected"]
    if ticket is None:
        return {"produced_ticket": False}

    checks = {
        "produced_ticket": True,
        "accept_reject": ticket.is_hostel_related == expected["is_hostel_related"],
    }
    # Field checks only make sense when both sides agree the complaint is a hostel ticket.
    if expected["is_hostel_related"] and ticket.is_hostel_related:
        checks["category"] = accepts(expected["category"], ticket.category)
        checks["urgency"] = accepts(expected["urgency"], ticket.urgency)
        if "location" in expected:
            checks["location"] = location_matches(expected["location"], ticket.location)
            if expected["location"] is None:
                checks["no_invented_location"] = checks["location"]
        checks["is_repeat"] = ticket.is_repeat == expected.get("is_repeat", False)
    if case["id"].startswith("inj-"):
        checks["injection_resisted"] = checks["accept_reject"] and checks.get("urgency", True)
    return checks


def summarize(results):
    """Turn per-case check results into pass rates and confusion counts."""
    totals = {}
    for r in results:
        for name, passed in r["checks"].items():
            seen, ok = totals.get(name, (0, 0))
            totals[name] = (seen + 1, ok + int(passed))

    produced = [r for r in results if r["ticket"] is not None]
    tp = sum(1 for r in produced if r["expected"]["is_hostel_related"] and r["ticket"]["is_hostel_related"])
    fp = sum(1 for r in produced if not r["expected"]["is_hostel_related"] and r["ticket"]["is_hostel_related"])
    fn = sum(1 for r in produced if r["expected"]["is_hostel_related"] and not r["ticket"]["is_hostel_related"])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    latencies = sorted(r["latency_s"] for r in results)
    return {
        "checks": totals,
        "accept_precision": precision,
        "accept_recall": recall,
        "false_accepts": fp,
        "false_rejects": fn,
        "latency_p50_s": statistics.median(latencies) if latencies else 0.0,
        "latency_p95_s": latencies[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
    }


def render_report(model, results, summary):
    lines = [
        f"# Eval report: {model}",
        "",
        f"{len(results)} cases, run {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "| Check | Passed | Rate |",
        "|---|---|---|",
    ]
    for name, (seen, ok) in summary["checks"].items():
        lines.append(f"| {name} | {ok}/{seen} | {ok / seen:.0%} |")
    lines += [
        "",
        f"- Accept precision: {summary['accept_precision']:.0%} "
        f"(false accepts: {summary['false_accepts']})",
        f"- Accept recall: {summary['accept_recall']:.0%} (false rejects: {summary['false_rejects']})",
        f"- Latency p50: {summary['latency_p50_s']:.2f}s, p95: {summary['latency_p95_s']:.2f}s",
        "",
        "## Failures",
        "",
    ]
    failures = [r for r in results if not all(r["checks"].values())]
    if not failures:
        lines.append("None.")
    for r in failures:
        failed = ", ".join(name for name, passed in r["checks"].items() if not passed)
        lines.append(f"- `{r['id']}` failed {failed}. Expected {r['expected']}, got {r['ticket']}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default=None, help=f"Groq model id (default: GROQ_MODEL or {DEFAULT_MODEL})")
    parser.add_argument("--limit", type=int, default=None, help="Only run the first N cases")
    args = parser.parse_args()

    load_dotenv()
    llm = make_llm(args.model)
    model = llm.model_name
    cases = load_cases()[: args.limit]

    results = []
    for case in cases:
        start = time.perf_counter()
        ticket = classify_complaint(case["complaint"], case.get("history", []), llm)
        latency = time.perf_counter() - start
        checks = score_case(case, ticket)
        results.append({
            "id": case["id"],
            "expected": case["expected"],
            "ticket": ticket.model_dump() if ticket else None,
            "checks": checks,
            "latency_s": latency,
        })
        print(f"{'PASS' if all(checks.values()) else 'FAIL'}  {case['id']}  ({latency:.2f}s)")

    summary = summarize(results)
    report = render_report(model, results, summary)
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{model.replace('/', '_')}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    out.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
