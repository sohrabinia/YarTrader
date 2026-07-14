from datetime import datetime, timedelta
from typing import List
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Application.Demo.models import DemoScenario


def generate_market_points(
    asset: str,
    base_price: float,
    trend_slope: float,
    volatility: float,
    volume: float,
    count: int = 10
) -> List[MarketDataPoint]:
    """Helper to generate a realistic sequence of MarketDataPoints."""
    points = []
    current_time = datetime.now() - timedelta(days=count)
    price = base_price

    for i in range(count):
        # Apply a drift (trend) and some random-like deterministic fluctuation
        drift = trend_slope * (i + 1)
        fluctuation = (i % 3 - 1) * volatility * price
        close_price = base_price + drift + fluctuation
        open_price = base_price + trend_slope * i + (i % 2 - 0.5) * volatility * price

        high_price = max(open_price, close_price) + abs(fluctuation) * 0.5
        low_price = min(open_price, close_price) - abs(fluctuation) * 0.5

        # Avoid <= 0 prices
        close_price = max(1.0, close_price)
        open_price = max(1.0, open_price)
        high_price = max(open_price, close_price, high_price)
        low_price = max(1.0, min(open_price, close_price, low_price))

        points.append(
            MarketDataPoint(
                AssetId=asset,
                Timestamp=current_time,
                Open=round(open_price, 4),
                High=round(high_price, 4),
                Low=round(low_price, 4),
                Close=round(close_price, 4),
                Volume=volume
            )
        )
        current_time += timedelta(days=1)

    return points


def create_trend_continuation_scenario(asset: str = "EURUSD") -> DemoScenario:
    """Generates scenario: Strong bullish continuation, healthy volume, low volatility."""
    # Strong upward trend
    price_data = generate_market_points(
        asset=asset,
        base_price=1.1000,
        trend_slope=0.0150,  # upward
        volatility=0.002,    # low volatility
        volume=100000.0,
        count=10
    )
    return DemoScenario(
        scenario_id="demo-trend-continuation",
        name="Trend Continuation Scenario",
        description="Demonstrates strong bullish momentum with high liquidity and low volatility. Expected result: APPROVED.",
        asset=asset,
        timeframe="H1",
        price_data=price_data,
        parameters={"scenario_type": "TrendContinuation"}
    )


def create_trend_reversal_scenario(asset: str = "EURUSD") -> DemoScenario:
    """Generates scenario: Price moves up then falls sharply with high volatility, suggesting reversal."""
    # Bullish drift initially, but last points drop significantly
    points = generate_market_points(
        asset=asset,
        base_price=1.1000,
        trend_slope=0.0100,
        volatility=0.005,
        volume=80000.0,
        count=8
    )
    # Append reversal bars
    last_time = points[-1].Timestamp
    reversal_points = [
        MarketDataPoint(
            AssetId=asset,
            Timestamp=last_time + timedelta(days=1),
            Open=1.1800,
            High=1.1850,
            Low=1.1500,
            Close=1.1550,
            Volume=120000.0
        ),
        MarketDataPoint(
            AssetId=asset,
            Timestamp=last_time + timedelta(days=2),
            Open=1.1550,
            High=1.1600,
            Low=1.1200,
            Close=1.1250,
            Volume=150000.0
        )
    ]
    price_data = points + reversal_points
    return DemoScenario(
        scenario_id="demo-trend-reversal",
        name="Trend Reversal Scenario",
        description="Demonstrates an initial bullish trend that experiences a sudden sharp reversal on rising volume. Expected result: REJECTED or REVIEW_REQUIRED.",
        asset=asset,
        timeframe="H1",
        price_data=price_data,
        parameters={"scenario_type": "TrendReversal"}
    )


def create_high_volatility_scenario(asset: str = "EURUSD") -> DemoScenario:
    """Generates scenario: Extreme price range oscillations to test risk boundary triggers."""
    # Extreme volatility
    price_data = generate_market_points(
        asset=asset,
        base_price=1.1000,
        trend_slope=0.0010,
        volatility=0.080,  # 8% daily fluctuations (very high)
        volume=250000.0,
        count=10
    )
    return DemoScenario(
        scenario_id="demo-high-volatility",
        name="High Volatility Scenario",
        description="Demonstrates extreme price range oscillations, exceeding default risk-tolerance thresholds. Expected result: REJECTED.",
        asset=asset,
        timeframe="H1",
        price_data=price_data,
        parameters={"scenario_type": "HighVolatility", "restrict_risk": True}
    )


def create_low_liquidity_scenario(asset: str = "EURUSD") -> DemoScenario:
    """Generates scenario: Flat price movement with extremely low trading volumes."""
    # Flat price, near-zero volume
    price_data = generate_market_points(
        asset=asset,
        base_price=1.1000,
        trend_slope=0.0000,
        volatility=0.0005,
        volume=100.0,  # extremely low volume
        count=10
    )
    return DemoScenario(
        scenario_id="demo-low-liquidity",
        name="Low Liquidity Scenario",
        description="Demonstrates flat price movement coupled with minimal trading volume, inducing quality penalties. Expected result: REVIEW_REQUIRED or INSUFFICIENT_DATA.",
        asset=asset,
        timeframe="H1",
        price_data=price_data,
        parameters={"scenario_type": "LowLiquidity"}
    )


def create_conflicting_signals_scenario(asset: str = "EURUSD") -> DemoScenario:
    """Generates scenario: Technical indicators suggest opposite actions, triggering conflict engines."""
    # Upward close prices, but with low volume and large high-low spreads
    price_data = generate_market_points(
        asset=asset,
        base_price=1.1000,
        trend_slope=0.0120,
        volatility=0.015,
        volume=20000.0,
        count=10
    )
    return DemoScenario(
        scenario_id="demo-conflicting-signals",
        name="Conflicting Signals Scenario",
        description="Demonstrates technical indicators suggesting opposite forces (e.g., rising prices on falling volumes/low strategy scores). Expected result: REVIEW_REQUIRED.",
        asset=asset,
        timeframe="H1",
        price_data=price_data,
        parameters={"scenario_type": "ConflictingSignals", "induce_conflict": True}
    )


def load_scenario_library(asset: str = "EURUSD") -> List[DemoScenario]:
    """Returns a list of all five ready-to-run demo scenarios."""
    return [
        create_trend_continuation_scenario(asset),
        create_trend_reversal_scenario(asset),
        create_high_volatility_scenario(asset),
        create_low_liquidity_scenario(asset),
        create_conflicting_signals_scenario(asset)
    ]
