import pytest
from src.Intelligence.Explanation.explainer import DecisionExplainer


def test_explain_why_open_trade_answers():
    """Checks that question 'Why did you open this trade' is parsed and answered correctly in both languages."""
    explainer = DecisionExplainer()

    # 1. English
    ans_en = explainer.answer_question("Why did you open this trade?", lang="en")
    assert "Decision: BUY XAUUSD" in ans_en
    assert "Evidence" in ans_en
    assert "Confidence: 72%" in ans_en or "Confidence: 72" in ans_en
    assert "Risk: High volatility event detected" in ans_en

    # 2. Persian (Autodetect language)
    ans_fa = explainer.answer_question("چرا این معامله را باز کردی؟")
    assert "تصمیم" in ans_fa
    assert "شواهد" in ans_fa
    assert "سطح اطمینان" in ans_fa


def test_explain_why_no_trade_answers():
    """Checks that question 'Why didn't you trade' is parsed and answered correctly in both languages."""
    explainer = DecisionExplainer()

    # 1. English
    ans_en = explainer.answer_question("Why didn't you trade?", lang="en")
    assert "No trade executed." in ans_en
    assert "Only 14 similar cases found." in ans_en or "Only 14 similar cases found" in ans_en
    assert "Insufficient evidence." in ans_en or "Insufficient evidence" in ans_en

    # 2. Persian (Autodetect language)
    ans_fa = explainer.answer_question("چرا معامله نکردی؟")
    assert "معامله‌ای انجام نشد." in ans_fa or "معامله" in ans_fa
    assert "۱۴" in ans_fa or "14" in ans_fa
