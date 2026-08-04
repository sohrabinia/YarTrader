from datetime import datetime
from typing import Dict, Any, List

class UserIntelligenceAgent:
    """
    User Intelligence Agent tracks reading behavior, interaction frequency, and signal engagement
    to dynamically segment users into clear profiles.
    """

    def __init__(self, agent_id: str = "agent-user-intel"):
        self.agent_id = agent_id

    def profile_user(self, user_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        articles_read = telemetry.get("articles_read", 0)
        shadow_trades_watched = telemetry.get("shadow_trades_watched", 0)
        time_spent_sec = telemetry.get("time_spent_sec", 0)

        # Dynamic Segment logic
        if articles_read >= 10 and shadow_trades_watched >= 15:
            segment = "Research User"
        elif shadow_trades_watched >= 8:
            segment = "Professional"
        elif articles_read >= 5:
            segment = "Intermediate"
        elif articles_read > 0 or time_spent_sec > 60:
            segment = "Beginner"
        else:
            segment = "Investor"

        return {
            "user_id": user_id,
            "segment": segment,
            "profiled_at": datetime.utcnow().isoformat() + "Z",
            "telemetry_metrics": {
                "articles_read": articles_read,
                "shadow_trades_watched": shadow_trades_watched,
                "time_spent_sec": time_spent_sec
            }
        }


class GrowthAgent:
    """
    Growth Agent monitors user acquisition, retention rate, and engagement.
    """

    def __init__(self, agent_id: str = "agent-growth"):
        self.agent_id = agent_id

    def calculate_growth_metrics(self, current_period_users: int, previous_period_users: int, active_users: int) -> Dict[str, Any]:
        retention_rate = (active_users / current_period_users) * 100.0 if current_period_users > 0 else 0.0
        user_acquisition_growth = 0.0
        if previous_period_users > 0:
            user_acquisition_growth = ((current_period_users - previous_period_users) / previous_period_users) * 100.0

        return {
            "retention_rate_pct": round(retention_rate, 2),
            "acquisition_growth_rate_pct": round(user_acquisition_growth, 2),
            "calculated_at": datetime.utcnow().isoformat() + "Z"
        }


class ConversionAgent:
    """
    Conversion Agent tracks conversion funnel stages.
    Funnel: Visitor -> Content Reader -> Registered User -> Active User -> Premium Candidate.
    """

    def __init__(self, agent_id: str = "agent-conversion"):
        self.agent_id = agent_id

    def track_funnel(self, funnel_data: Dict[str, int]) -> Dict[str, Any]:
        visitors = funnel_data.get("visitors", 1000)
        readers = funnel_data.get("readers", 500)
        registered = funnel_data.get("registered", 100)
        active = funnel_data.get("active", 50)
        premium_candidates = funnel_data.get("premium_candidates", 10)

        # Conversions relative to previous stages
        reader_conv = (readers / visitors) * 100.0 if visitors > 0 else 0.0
        reg_conv = (registered / readers) * 100.0 if readers > 0 else 0.0
        active_conv = (active / registered) * 100.0 if registered > 0 else 0.0
        premium_conv = (premium_candidates / active) * 100.0 if active > 0 else 0.0

        # Overall conversion rate (Visitor to Registered)
        overall_sign_up_rate = (registered / visitors) * 100.0 if visitors > 0 else 0.0

        return {
            "funnel_stages": {
                "visitors": visitors,
                "readers": readers,
                "registered": registered,
                "active": active,
                "premium_candidates": premium_candidates
            },
            "conversion_ratios_pct": {
                "visitor_to_reader": round(reader_conv, 2),
                "reader_to_registered": round(reg_conv, 2),
                "registered_to_active": round(active_conv, 2),
                "active_to_premium": round(premium_conv, 2)
            },
            "overall_conversion_sign_up_rate_pct": round(overall_sign_up_rate, 2),
            "audited_at": datetime.utcnow().isoformat() + "Z"
        }
