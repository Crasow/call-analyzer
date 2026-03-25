import uuid

import pytest

from call_analyzer.analyzer import (
    ANALYSIS_PROMPT,
    _create_analysis_result,
    _create_profile_result,
    _parse_gemini_response,
    build_prompt,
)
from call_analyzer.models import Profile


# ── _parse_gemini_response ───────────────────────────────────────────

def test_parse_gemini_response():
    raw = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"transcript": "Hello", "is_fraud": true, "fraud_score": 0.9, "fraud_categories": ["Vishing"], "reasons": ["Suspicious"]}'
                        }
                    ]
                }
            }
        ]
    }
    parsed = _parse_gemini_response(raw)
    assert parsed["is_fraud"] is True
    assert parsed["fraud_score"] == 0.9
    assert parsed["transcript"] == "Hello"
    assert "Vishing" in parsed["fraud_categories"]
    assert "Suspicious" in parsed["reasons"]


def test_parse_gemini_response_clean():
    raw = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": '{"transcript": "Normal call", "is_fraud": false, "fraud_score": 0.1, "fraud_categories": [], "reasons": []}'
                        }
                    ]
                }
            }
        ]
    }
    parsed = _parse_gemini_response(raw)
    assert parsed["is_fraud"] is False
    assert parsed["fraud_score"] == 0.1


def test_parse_gemini_response_markdown_fences():
    raw = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": '```json\n{"key": "value"}\n```'}
                    ]
                }
            }
        ]
    }
    parsed = _parse_gemini_response(raw)
    assert parsed["key"] == "value"


def test_parse_gemini_response_missing_candidates():
    with pytest.raises(ValueError, match="Unexpected Gemini response"):
        _parse_gemini_response({})


def test_parse_gemini_response_empty_candidates():
    with pytest.raises(ValueError, match="Unexpected Gemini response"):
        _parse_gemini_response({"candidates": []})


def test_parse_gemini_response_invalid_json():
    raw = {
        "candidates": [
            {"content": {"parts": [{"text": "not json at all"}]}}
        ]
    }
    with pytest.raises(ValueError, match="invalid JSON"):
        _parse_gemini_response(raw)


def test_parse_gemini_response_require_fraud_fields_missing():
    raw = {
        "candidates": [
            {"content": {"parts": [{"text": '{"transcript": "hi"}'}]}}
        ]
    }
    with pytest.raises(ValueError, match="missing 'is_fraud'"):
        _parse_gemini_response(raw, require_fraud_fields=True)


def test_parse_gemini_response_require_fraud_fields_ok():
    raw = {
        "candidates": [
            {"content": {"parts": [{"text": '{"is_fraud": false, "fraud_score": 0.1}'}]}}
        ]
    }
    parsed = _parse_gemini_response(raw, require_fraud_fields=True)
    assert parsed["is_fraud"] is False


# ── build_prompt ─────────────────────────────────────────────────────

def test_build_prompt_no_profile():
    assert build_prompt(None) == ANALYSIS_PROMPT


def test_build_prompt_custom_mode():
    profile = Profile(
        id=uuid.uuid4(), name="test", prompt_mode="custom",
        custom_prompt="My custom prompt",
    )
    assert build_prompt(profile) == "My custom prompt"


def test_build_prompt_template_mode():
    profile = Profile(
        id=uuid.uuid4(), name="test", prompt_mode="template",
        main_task="Analyze sentiment",
        expert="анализ настроений",
        fields_for_json="sentiment, confidence",
    )
    result = build_prompt(profile)
    assert "анализ настроений" in result
    assert "Analyze sentiment" in result
    assert "sentiment, confidence" in result


def test_build_prompt_template_mode_default_expert():
    profile = Profile(
        id=uuid.uuid4(), name="test", prompt_mode="template",
        main_task="Do analysis",
    )
    result = build_prompt(profile)
    assert "анализ телефонных разговоров" in result


def test_build_prompt_trigger_words_only():
    profile = Profile(
        id=uuid.uuid4(), name="test", prompt_mode="custom",
        trigger_words=["кредит", "долг"],
    )
    result = build_prompt(profile)
    assert "кредит" in result
    assert "долг" in result


def test_build_prompt_custom_with_triggers():
    profile = Profile(
        id=uuid.uuid4(), name="test", prompt_mode="custom",
        custom_prompt="Analyze this",
        trigger_words=["word1"],
    )
    result = build_prompt(profile)
    assert result.startswith("Analyze this")
    assert "word1" in result


# ── Result helpers ───────────────────────────────────────────────────

def test_create_analysis_result():
    call_id = uuid.uuid4()
    parsed = {
        "transcript": "hi",
        "is_fraud": True,
        "fraud_score": 0.95,
        "fraud_categories": ["Vishing"],
        "reasons": ["suspicious"],
    }
    result = _create_analysis_result(parsed, call_id)
    assert result.call_id == call_id
    assert result.is_fraud is True
    assert result.fraud_score == 0.95


def test_create_profile_result():
    call_id = uuid.uuid4()
    parsed = {"transcript": "hello", "sentiment": "positive"}
    result = _create_profile_result(parsed, call_id)
    assert result.call_id == call_id
    assert result.data == parsed
    assert result.transcript == "hello"
