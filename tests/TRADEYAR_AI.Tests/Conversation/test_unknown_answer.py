import pytest
from src.Intelligence.Explanation.explainer import DecisionExplainer


def test_explain_what_not_known_answers():
    """Checks that question 'What don't you know' is answered properly."""
    explainer = DecisionExplainer()

    # 1. English
    ans_en = explainer.answer_question("What don't you know?", lang="en")
    assert "Insufficient knowledge." in ans_en or "Insufficient knowledge" in ans_en
    assert "Only 5 historical examples exist." in ans_en or "Only 5 historical examples exist" in ans_en
    assert "Confidence too low." in ans_en or "Confidence too low" in ans_en

    # 2. Persian (Autodetect language)
    ans_fa = explainer.answer_question("چه چیزی را نمی‌دانی؟")
    assert "دانش ناکافی." in ans_fa or "دانش" in ans_fa
    assert "۵" in ans_fa or "5" in ans_fa
    assert "سطح اطمینان بسیار پایین است." in ans_fa or "سطح اطمینان" in ans_fa
