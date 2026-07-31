import pytest
from src.Intelligence.Explanation.explainer import DecisionExplainer


def test_explain_what_learned_answers():
    """Checks that question 'What did you learn' is answered properly."""
    explainer = DecisionExplainer()

    # 1. English
    ans_en = explainer.answer_question("What did you learn?", lang="en")
    assert "New pattern discovered: Gold reversal after London open" in ans_en
    assert "Occurrences: 312" in ans_en
    assert "Accuracy: 69%" in ans_en

    # 2. Persian (Autodetect language)
    ans_fa = explainer.answer_question("چه چیزی یاد گرفتی؟")
    assert "الگوی جدید کشف شد" in ans_fa
    assert "۳۱۲" in ans_fa or "312" in ans_fa
    assert "۶۹٪" in ans_fa or "69٪" in ans_fa


def test_explain_mistake_answers():
    """Checks that question 'Where did you make a mistake' is answered properly."""
    explainer = DecisionExplainer()

    # 1. English
    ans_en = explainer.answer_question("Where did you make a mistake?", lang="en")
    assert "Prediction: Continuation" in ans_en
    assert "Reality: Reversal" in ans_en
    assert "Failure reason: Historical samples lacked news volatility cases" in ans_en

    # 2. Persian (Autodetect language)
    ans_fa = explainer.answer_question("کجا اشتباه کردی؟")
    assert "پیش‌بینی" in ans_fa
    assert "واقعیت" in ans_fa
    assert "دلیل شکست" in ans_fa
