"""Evals: dataset-driven angle evaluation with judge model."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from gtm_enrich.llm import complete_json
from gtm_enrich.models import Angle, Channel, EvalResult, ResearchBrief

EVAL_SYSTEM = (
    "You are an expert GTM evaluator. Given an outbound angle, company context, "
    "and evaluation rules, determine if the angle passes each rule.\n\n"
    "Output JSON with:\n"
    "- rule_checks: dict[rule_name -> bool]\n"
    "- judge_scores: dict[criteria -> int] (1-5 scale)\n"
    "- judge_reason: 1-2 sentence explanation\n"
    "- passed: bool (true if ALL rule_checks are true)\n\n"
    "Rules to check:\n"
    "1. specific_to_company: Angle references specific company details (not generic)\n"
    "2. cites_signals: Angle explicitly cites signal IDs in brackets\n"
    "3. actionable: Angle has clear next step / call to action\n"
    "4. appropriate_tone: Professional, not spammy, respects recipient\n"
    "5. channel_fit: Angle suits the channel (email vs LinkedIn)\n"
    "6. no_hallucination: Angle doesn't invent facts not in signals"
)

EVAL_USER_TEMPLATE = (
    "Company: {company}\n"
    "Angle: {angle}\n"
    "Channel: {channel}\n"
    "Cited Signals: {signal_texts}\n\n"
    "Evaluate against the 6 rules above. Return JSON only."
)


async def evaluate_angle(
    angle: Angle,
    company: str,
) -> EvalResult:
    """Evaluate a single angle using judge model."""
    signal_texts = " | ".join(angle.signal_ids)

    user = EVAL_USER_TEMPLATE.format(
        company=company,
        angle=angle.text,
        channel=angle.channel.value,
        signal_texts=signal_texts,
    )

    try:
        return complete_json(
            schema=EvalResult,
            system=EVAL_SYSTEM,
            user=user,
            model="nim-step",
        )
    except Exception as e:
        return EvalResult(
            angle=angle.text,
            company=company,
            rule_checks={},
            judge_scores={},
            judge_reason=f"Evaluation failed: {e}",
            passed=False,
        )


def load_dataset(path: Path) -> list[dict[str, Any]]:
    """Load eval dataset from CSV or JSONL."""
    if path.suffix == ".csv":
        with path.open() as f:
            reader = csv.DictReader(f)
            return list(reader)
    elif path.suffix == ".jsonl":
        with path.open() as f:
            return [json.loads(line) for line in f]
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")


async def run_evals(
    dataset_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Run evaluation on dataset of (company, angle, expected_pass)."""
    dataset = load_dataset(dataset_path)

    results = []
    passed = 0

    for row in dataset:
        company = row.get("company", "")
        angle_text = row.get("angle", "")
        channel = row.get("channel", "email")
        expected = row.get("expected_pass", "true").lower() == "true"

        channel_enum = Channel.EMAIL if channel == "email" else Channel.LINKEDIN
        angle = Angle(
            text=angle_text,
            signal_ids=[],
            channel=channel_enum,
        )

        ResearchBrief(
            summary="",
            icp_fit_score=3,
            fit_reason="",
            angles=[angle],
        )

        result = await evaluate_angle(angle, company)
        results.append(
            {
                "company": company,
                "angle": angle_text,
                "expected": expected,
                "actual": result.passed,
                "rule_checks": result.rule_checks,
                "judge_scores": result.judge_scores,
                "judge_reason": result.judge_reason,
            }
        )
        if result.passed == expected:
            passed += 1

    accuracy = passed / len(dataset) if dataset else 0.0

    summary = {
        "total": len(dataset),
        "passed": passed,
        "accuracy": accuracy,
        "results": results,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(summary, f, indent=2)

    return summary