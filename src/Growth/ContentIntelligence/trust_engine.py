import re
import datetime
from typing import Dict, Any, List

class TrustReviewEngine:
    """
    Extensible validation engine that chains multiple rule scans to evaluate content
    compliance, security standards, and append disclosures. Supports bilingual English and Persian rule checks.
    """

    def __init__(self) -> None:
        pass

    def scan_draft(self, draft: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the chained validation pipeline on the provided draft.
        """
        violations: List[Dict[str, Any]] = []
        disclosures: List[str] = []
        body_text = draft.get("body", "")
        title_text = draft.get("title", "")
        full_text = f"{title_text}\n{body_text}".lower()
        lang = draft.get("language", "en").lower()

        # 1. Financial Claim Rules (English & Persian)
        claim_patterns = [
            # English profit guarantees
            (r"(guaranteed?|promise|100%|always)\s+(profit|win|gain|return|yield)", "Profit guarantees or win rate promises are strictly prohibited."),
            (r"(double\s+your|get\s+rich)", "Unverified financial hype or get-rich-quick claims are prohibited."),
            (r"(\b\d{1,3}%\s+profit|\b\d{1,3}%\s+daily\b)", "Absolute performance figures or daily return percentages are prohibited."),
            # Persian profit guarantees (e.g. تضمینی، سود، تضمین، ۱۰۰٪، همیشه)
            (r"(تضمین|تضمینی|صد\s*در\s*صد|۱۰۰٪|همیشه)\s+.*(سود|بازده|برد|پیروزی|درآمد)", "ارائه تضمین سود یا درصد برد به هر نحو اکیداً ممنوع است."),
            (r"(سود\s*تضمین)", "ارائه سود تضمین شده ممنوع است."),
            # Persian percentage checks (matching digits like 20% or ۲۰٪)
            (r"(\b\d{1,3}٪\s*سود|\b[۰-۹]{1,3}٪\s*سود|\b[۰-۹]{1,3}\s*درصد\s*سود)", "ذکر درصد بازدهی مشخص یا سود قطعی روزانه/ماهانه ممنوع است.")
        ]
        for pattern, msg in claim_patterns:
            if re.search(pattern, full_text):
                violations.append({
                    "rule_id": "FinancialClaimRules",
                    "severity": "REJECT",
                    "message": msg
                })

        # 2. Signal Language Rules (English & Persian)
        signal_patterns = [
            # English signal commands
            (r"(must|should|buy|sell|trade)\s+(now|immediately|this\s+asset)", "Direct buy/sell execution commands or signal-selling prose are strictly prohibited."),
            (r"(signal\s+selling|paid\s+signals)", "Promotion of signal-selling services is prohibited under simulation-only guidelines."),
            # Persian signal commands (e.g. خرید، فروش، معامله کنید، الان، فوری)
            (r"(خرید|فروش|معامله)\s+(فوری|الان|سریع|در\s*حال\s*حاضر)", "ارائه دستورات مستقیم خرید و فروش یا سیگنال‌دهی اکیداً ممنوع است."),
            (r"(کانال\s*سیگنال|سیگنال\s*خرید|سیگنال\s*فروش)", "هرگونه تبلیغ یا ارائه خدمات سیگنال‌دهی ممنوع است.")
        ]
        for pattern, msg in signal_patterns:
            if re.search(pattern, full_text):
                violations.append({
                    "rule_id": "SignalLanguageRules",
                    "severity": "REJECT",
                    "message": msg
                })

        # 3. Source Verification Rules
        source_id = draft.get("source_intelligence_id")
        if not source_id or len(str(source_id).strip()) < 3:
            violations.append({
                "rule_id": "SourceVerificationRules",
                "severity": "FLAG",
                "message": "Content must retain valid reference lineage mapping back to underlying research source IDs."
            })

        # 4. Disclosure Rules
        # Automatically append risk disclaimers based on target language
        if lang == "fa":
            disclosure_msg = (
                "سلب مسئولیت: تمامی تحلیل‌ها و داده‌های ارائه شده توسط TradeYar AI صرفاً جنبه آموزشی و شبیه‌سازی دارند "
                "و به هیچ عنوان توصیه مالی، مشاوره سرمایه‌گذاری یا سیگنال خرید و فروش محسوب نمی‌شوند. "
                "عملکرد گذشته شبیه‌ساز تضمین‌کننده سودآوری آینده نیست."
            )
        else:
            disclosure_msg = (
                "DISCLAIMER: All TradeYar AI analyses are for simulated and educational purposes only. "
                "This does not constitute financial advice, buy/sell trading signals, or investment recommendations. "
                "Past simulation metrics do not guarantee future profitability."
            )
        disclosures.append(disclosure_msg)

        # Evaluate final status
        status = "APPROVED"
        for v in violations:
            if v["severity"] == "REJECT":
                status = "REJECTED"
                break
            elif v["severity"] == "FLAG":
                status = "FLAGGED"

        # If approved or flagged but has disclosures, append disclaimer to body safely
        appended_body = body_text
        if status != "REJECTED" and disclosures:
            appended_body = f"{body_text}\n\n---\n" + "\n".join(disclosures)

        return {
            "status": status,
            "violations": violations,
            "disclosures": disclosures,
            "appended_body": appended_body,
            "reviewed_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z"
        }
