"""M7 evals tests."""

from __future__ import annotations

import json

import pytest

from gtm_enrich.evals import evaluate_angle, load_dataset, run_evals
from gtm_enrich.models import Angle, Channel, EvalResult, ResearchBrief

EXPECTED_TOTAL = 2


@pytest.mark.asyncio
async def test_evaluate_angle_passes():
    """Evaluate a good angle that should pass."""
    angle = Angle(
        text="Saw you're hiring Senior Engineers [s2] - our tool cuts onboarding time by 50%",
        signal_ids=["s2"],
        channel=Channel.EMAIL,
    )
    ResearchBrief(
        summary="Test company",
        icp_fit_score=4,
        fit_reason="Good fit",
        angles=[angle],
    )

    result = await evaluate_angle(angle, "test.com")

    # Should have rule checks
    assert isinstance(result.rule_checks, dict)
    assert isinstance(result.judge_scores, dict)
    assert result.judge_reason


@pytest.mark.asyncio
async def test_load_dataset_csv(tmp_path):
    """Load dataset from CSV."""
    csv_path = tmp_path / "eval.csv"
    csv_path.write_text("company,angle,channel,expected_pass\nexample.com,Test angle,email,true\n")

    dataset = load_dataset(csv_path)

    assert len(dataset) == 1
    assert dataset[0]["company"] == "example.com"
    assert dataset[0]["expected_pass"] == "true"


@pytest.mark.asyncio
async def test_load_dataset_jsonl(tmp_path):
    """Load dataset from JSONL."""
    jsonl_path = tmp_path / "eval.jsonl"
    jsonl_path.write_text(
        '{"company": "test.com", "angle": "Test", "channel": "linkedin", '
        '"expected_pass": "false"}\n'
    )

    dataset = load_dataset(jsonl_path)

    assert len(dataset) == 1
    assert dataset[0]["company"] == "test.com"
    assert dataset[0]["expected_pass"] == "false"


@pytest.mark.asyncio
async def test_run_evals_creates_output(tmp_path):
    """Run evals and verify output file."""
    jsonl_path = tmp_path / "eval.jsonl"
    jsonl_path.write_text(
        '{"company": "a.com", "angle": "Good angle citing [s0]", '
        '"channel": "email", "expected_pass": "true"}\n'
        '{"company": "b.com", "angle": "Generic spam", '
        '"channel": "email", "expected_pass": "false"}\n'
    )
    output_path = tmp_path / "results.json"

    summary = await run_evals(jsonl_path, output_path)

    assert summary["total"] == EXPECTED_TOTAL
    assert "accuracy" in summary
    assert output_path.exists()

    with output_path.open() as f:
        data = json.load(f)
    assert data["total"] == EXPECTED_TOTAL


@pytest.mark.asyncio
async def test_eval_result_model():
    """EvalResult model validation."""
    result = EvalResult(
        angle="Test angle",
        company="test.com",
        rule_checks={"specific_to_company": True, "cites_signals": True},
        judge_scores={"relevance": 4, "clarity": 5},
        judge_reason="Good angle",
        passed=True,
    )

    assert result.passed is True
    assert result.rule_checks["specific_to_company"] is True