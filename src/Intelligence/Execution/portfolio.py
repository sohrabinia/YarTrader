from typing import List, Dict, Any, Optional

class PortfolioRiskIntelligenceEngine:
    """
    Computes portfolio-level risk metrics, including total exposure, concentration,
    heat, correlation exposure, and drawdown risk. Enforces strict governance rules
    to block advisory execution plans if portfolio limits are breached.
    """
    def __init__(
        self,
        max_heat_pct: float = 6.0,
        max_concentration_pct: float = 30.0,
        max_correlation_exposure_pct: float = 15.0,
        max_risk_per_trade_pct: float = 0.5,
        max_strategy_exposure_ceiling_pct: float = 3.0,
        max_daily_drawdown_pct: float = 10.0,
        start_of_day_equity: Optional[float] = None,
        daily_pnl: float = 0.0
    ) -> None:
        self.max_heat_pct = max_heat_pct
        self.max_concentration_pct = max_concentration_pct
        self.max_correlation_exposure_pct = max_correlation_exposure_pct
        self.max_risk_per_trade_pct = max_risk_per_trade_pct
        self.max_strategy_exposure_ceiling_pct = max_strategy_exposure_ceiling_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.start_of_day_equity = start_of_day_equity
        self.daily_pnl = daily_pnl

    def calculate_portfolio_risk(
        self,
        active_trades: List[Dict[str, Any]],
        virtual_balance: float = 10000.0,
        start_of_day_equity: Optional[float] = None,
        daily_pnl: float = 0.0
    ) -> Dict[str, Any]:
        """
        Processes active trades to evaluate overall portfolio exposure and risk indicators.
        """
        total_exposure = 0.0
        portfolio_heat = 0.0
        asset_exposure: Dict[str, float] = {}

        # 1. Compute Exposure and Heat (risk per trade)
        for t in active_trades:
            if t.get("status") not in ["CREATED", "RUNNING"]:
                continue

            entry = float(t.get("entry", 1.0))
            stop = float(t.get("stop", 1.0))
            volume = float(t.get("volume", 1.0))
            sym = t.get("symbol", "UNKNOWN").upper()

            # Risk = entry to stop distance * volume * multiplier
            multiplier = 100.0 if "XAU" in sym else 10000.0
            trade_risk = abs(entry - stop) * multiplier * volume
            trade_exposure = entry * volume * multiplier

            total_exposure += trade_exposure
            portfolio_heat += (trade_risk / virtual_balance) * 100.0
            asset_exposure[sym] = asset_exposure.get(sym, 0.0) + trade_exposure

        # 2. Compute Concentrations
        concentrations = {}
        highest_concentration = 0.0
        for sym, exp in asset_exposure.items():
            pct = (exp / total_exposure * 100.0) if total_exposure > 0.0 else 0.0
            concentrations[sym] = round(pct, 2)
            if pct > highest_concentration:
                highest_concentration = pct

        # 3. Correlation Exposure Grouping (e.g. metals, forex, crypto correlations)
        # Gold/Silver have positive correlations. EURUSD/GBPUSD have positive correlations.
        correlation_exposure = 0.0
        metals_exp = asset_exposure.get("XAUUSD", 0.0) + asset_exposure.get("XAGUSD", 0.0)
        forex_exp = asset_exposure.get("EURUSD", 0.0) + asset_exposure.get("GBPUSD", 0.0)

        metals_pct = (metals_exp / virtual_balance * 100.0) if virtual_balance > 0 else 0.0
        forex_pct = (forex_exp / virtual_balance * 100.0) if virtual_balance > 0 else 0.0
        correlation_exposure = max(metals_pct, forex_pct)

        # 4. Daily Drawdown Evaluation
        sod_eq = start_of_day_equity or self.start_of_day_equity or virtual_balance
        actual_daily_pnl = daily_pnl if daily_pnl != 0.0 else self.daily_pnl
        daily_dd_pct = 0.0
        if sod_eq > 0 and actual_daily_pnl < 0:
            daily_dd_pct = (abs(actual_daily_pnl) / sod_eq) * 100.0

        # 5. Check Governance Violations
        trade_risk_violation = False
        for t in active_trades:
            if t.get("status") in ["CREATED", "RUNNING"]:
                t_risk_pct = float(t.get("risk_pct", 0.0))
                if t_risk_pct > self.max_risk_per_trade_pct:
                    trade_risk_violation = True
                    break

        heat_violation = portfolio_heat > self.max_heat_pct
        concentration_violation = highest_concentration > self.max_concentration_pct
        correlation_violation = correlation_exposure > self.max_correlation_exposure_pct
        exposure_ceiling_violation = portfolio_heat > self.max_strategy_exposure_ceiling_pct
        daily_drawdown_violation = daily_dd_pct >= self.max_daily_drawdown_pct

        risk_approved = not (heat_violation or concentration_violation or correlation_violation or trade_risk_violation or exposure_ceiling_violation or daily_drawdown_violation)

        violations = []
        if trade_risk_violation:
            violations.append(f"Single trade risk exceeds max limit of {self.max_risk_per_trade_pct}% equity")
        if heat_violation:
            violations.append(f"Portfolio Heat ({portfolio_heat:.2f}%) exceeds system budget ({self.max_heat_pct}%)")
        if exposure_ceiling_violation:
            violations.append(f"Combined strategy exposure ({portfolio_heat:.2f}%) exceeds max ceiling ({self.max_strategy_exposure_ceiling_pct}%)")
        if concentration_violation:
            violations.append(f"Asset Concentration ({highest_concentration:.2f}%) exceeds max boundary ({self.max_concentration_pct}%)")
        if correlation_violation:
            violations.append(f"Correlation Cluster Exposure ({correlation_exposure:.2f}%) exceeds boundary ({self.max_correlation_exposure_pct}%)")
        if daily_drawdown_violation:
            violations.append(f"Daily drawdown ({daily_dd_pct:.2f}%) hit max daily loss threshold ({self.max_daily_drawdown_pct}% of SOD equity). Trading halted.")

        return {
            "total_exposure": round(total_exposure, 2),
            "portfolio_heat_pct": round(portfolio_heat, 2),
            "asset_concentrations_pct": concentrations,
            "correlation_exposure_pct": round(correlation_exposure, 2),
            "risk_budget_pct": round(max(0.0, 100.0 - portfolio_heat), 2),
            "drawdown_risk": "LOW" if portfolio_heat < 3.0 else ("MEDIUM" if portfolio_heat < 6.0 else "HIGH"),
            "approved": risk_approved,
            "violations": violations,
            "summary": "Portfolio risk meets SRE criteria." if risk_approved else f"Risk limit violation: {', '.join(violations)}"
        }
