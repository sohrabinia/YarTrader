from typing import List, Dict, Any, Optional

class ExplainableExecutionIntelligence:
    """
    Constructs comprehensive, clear, and bilingual (FA/EN) reasoning sequences
    supporting execution plan advice. Guarantees no "black box" decisions exist.
    """
    def __init__(self) -> None:
        pass

    def build_reasoning_array(self, action: str, alignment: str, confidence: float, trend: str, liquidity_event: Optional[str] = None, lang: str = "fa") -> List[str]:
        """
        Assembles explicit reasons backing up an execution advice.
        """
        reasons = []

        if lang == "fa":
            # 1. State trend direction
            if trend == "BULLISH":
                reasons.append("روند بازار صعودی است.")
            elif trend == "BEARISH":
                reasons.append("روند بازار نزولی است.")
            else:
                reasons.append("روند بازار خنثی است.")

            # 2. Alignment checks
            if "FULLY_ALIGNED" in alignment:
                reasons.append("همسویی کامل در ساختار چند-زمانه تایید شد.")
            elif "HIGH_TIMEFRAME" in alignment:
                reasons.append("روند تایم‌فریم بالا همسو است.")
            else:
                reasons.append("همسویی تایم‌فریم‌ها ضعیف یا ناقص است.")

            # 3. Liquidity event integration
            if liquidity_event:
                if "BUY_SIDE" in liquidity_event:
                    reasons.append("پاکسازی نقدینگی سمت خرید (BSL) شناسایی شد.")
                elif "SELL_SIDE" in liquidity_event:
                    reasons.append("پاکسازی نقدینگی سمت فروش (SSL) شناسایی شد.")

            # 4. Confidence level and general risk
            if confidence >= 80:
                reasons.append(f"سطح اطمینان بالا ({confidence:.0f}٪) بر اساس شواهد تاریخی.")
            else:
                reasons.append(f"سطح اطمینان متوسط ({confidence:.0f}٪). احتیاط توصیه می‌شود.")

            # 5. Non-trading compliance reminder
            reasons.append("معامله آزمایشی تحت شبیه‌سازی APES-FIN انجام می‌شود.")

        else: # EN
            if trend == "BULLISH":
                reasons.append("Market trend is Bullish.")
            elif trend == "BEARISH":
                reasons.append("Market trend is Bearish.")
            else:
                reasons.append("Market trend is Neutral/Ranging.")

            if "FULLY_ALIGNED" in alignment:
                reasons.append("Full multi-timeframe structural alignment confirmed.")
            elif "HIGH_TIMEFRAME" in alignment:
                reasons.append("High timeframe structures are aligned.")
            else:
                reasons.append("Timeframe alignment is weak or incomplete.")

            if liquidity_event:
                reasons.append(f"Liquidity swept: {liquidity_event}")

            if confidence >= 80:
                reasons.append(f"High historical confidence ({confidence:.0f}%) of successful pattern matches.")
            else:
                reasons.append(f"Moderate confidence level ({confidence:.0f}%). Extra caution recommended.")

            reasons.append("Simulated evaluation under strict APES-FIN passive compliance rules.")

        return reasons
