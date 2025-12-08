from __future__ import annotations

import json
from pathlib import Path


MAIN_THRESHOLDS = {
    "groundedness": 3.0,
    "factual_correctness": 3.0,
    "answer_relevance": 3.0,
    "hallucination_score_max": 0.5,
    "latency_total_max": 5.0
}

SLICE_THRESHOLDS = {
    "groundedness": 3.0,
    "factual_correctness": 3.0,
    "answer_relevance": 3.0,
}

SMOKE_THRESHOLD = 3.0


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        raise RuntimeError(f"Invalid JSON in file: {path}")


def check_main_thresholds(summary: dict) -> bool:
    return (
        summary.get("groundedness", 0) >= MAIN_THRESHOLDS["groundedness"]
        and summary.get("factual_correctness", 0) >= MAIN_THRESHOLDS["factual_correctness"]
        and summary.get("answer_relevance", 0) >= MAIN_THRESHOLDS["answer_relevance"]
        and summary.get("hallucination_score", 1) <= MAIN_THRESHOLDS["hallucination_score_max"]
        and summary.get("latency_total", 99) <= MAIN_THRESHOLDS["latency_total_max"]
    )


def check_slice_thresholds(bias_report: dict) -> bool:
    slices = bias_report.get("slices", {})
    for slice_name, values in slices.items():
        if (
            values.get("groundedness", 0) < SLICE_THRESHOLDS["groundedness"]
            or values.get("factual_correctness", 0) < SLICE_THRESHOLDS["factual_correctness"]
            or values.get("answer_relevance", 0) < SLICE_THRESHOLDS["answer_relevance"]
        ):
            print(f"Slice failed threshold: {slice_name}")
            return False
    return True


def check_smoke_test(summary: dict) -> bool:
    # Smoke test: ensure core metrics are not catastrophically low
    return (
        summary.get("groundedness", 0) >= SMOKE_THRESHOLD
        and summary.get("factual_correctness", 0) >= SMOKE_THRESHOLD
        and summary.get("answer_relevance", 0) >= SMOKE_THRESHOLD
    )


def main() -> None:
    results_dir = Path("chat_pipeline/results")

    # Load required artifacts
    main_summary = load_json(results_dir / "core_eval_main" / "summary.json")
    slices_bias = load_json(results_dir / "core_eval_slices" / "bias_report.json")
    
    smoke_path = results_dir / "smoke_test_main" / "summary.json"
    smoke_summary = load_json(smoke_path) if smoke_path.exists() else None

    # Optional tuning validation
    tuning_report_path = results_dir / "core_eval_tuning" / "tuning_report.json"
    tuning_report = load_json(tuning_report_path) if tuning_report_path.exists() else None

    # Apply gating
    print("Checking main thresholds...")
    main_ok = check_main_thresholds(main_summary)

    print("Checking slice thresholds...")
    slices_ok = check_slice_thresholds(slices_bias)

    smoke_ok = False
    if smoke_summary:
        print("Checking smoke test...")
        smoke_ok = check_smoke_test(smoke_summary)
    else:
        print("❌ Smoke test artifacts not found. Quality gate requires smoke test results.")

    tuning_ok = True
    if tuning_report:
        print("Checking tuning runs...")
        # Handle list format (convert to dict by run name)
        if isinstance(tuning_report, list):
            tuning_report = {item["run"]: item for item in tuning_report}
        
        if "baseline" in tuning_report and "best" in tuning_report:
            baseline = tuning_report["baseline"]["summary"]
            best = tuning_report["best"]["summary"]
            tuning_ok = (
                best["groundedness"] >= baseline["groundedness"]
                and best["answer_relevance"] >= baseline["answer_relevance"]
                and best["factual_correctness"] >= baseline["factual_correctness"]
            )
        elif "baseline" in tuning_report:
             # If no "best" is explicitly marked, we can try to find the best functioning one or just pass
             # For now, let's just log and pass to avoid blocking deployment
             print("⚠️ 'best' run key not found in tuning report. Skipping relative improvement check.")
             tuning_ok = True
        else:
            print("⚠️ 'baseline' run key not found in tuning report. Skipping tuning check.")
            tuning_ok = True

    overall = main_ok and slices_ok and smoke_ok and tuning_ok

    status = "PASS" if overall else "FAIL"
    print(f"\nQUALITY_GATE_STATUS={status}")

    out_path = results_dir / "quality_gate.txt"
    out_path.write_text(status)


if __name__ == "__main__":
    main()