from datetime import datetime
from typing import List, Optional
from src.Infrastructure.exceptions import ValidationException
from src.Data.MarketData.Models.models import MarketDataPoint
from src.Research.Features.interfaces import IFeaturePipeline
from src.Research.Features.models import MarketFeatureSet, FeatureValue
from src.Research.Features.registry import FeatureRegistry


class FeaturePipeline(IFeaturePipeline):
    """Orchestrates the feature calculation flow across registered calculators."""

    def __init__(self, registry: Optional[FeatureRegistry] = None) -> None:
        self._registry = registry or FeatureRegistry()

    @property
    def registry(self) -> FeatureRegistry:
        return self._registry

    def execute(self, data_points: List[MarketDataPoint]) -> MarketFeatureSet:
        """Processes standard data points to build a comprehensive MarketFeatureSet."""
        if not data_points:
            raise ValidationException("Validation Error: Cannot execute feature pipeline on empty data points.")

        # Determine boundaries
        asset_id = data_points[0].AssetId
        start_time = data_points[0].Timestamp
        end_time = data_points[-1].Timestamp

        features_dict = {}

        # Discover and execute calculators
        pairs = self._registry.get_calculators_by_definition()

        # If registry is empty, let's also support a default set of calculators
        if not pairs:
            # Fallback: if no calculators registered, we can register default ones
            from src.Research.Features.calculators import (
                PriceFeatureCalculator,
                VolatilityFeatureCalculator,
                TrendFeatureCalculator,
                StatisticalFeatureCalculator
            )
            from src.Research.Features.models import FeatureDefinition

            # Auto register defaults for ease of use
            price_calc = PriceFeatureCalculator()
            self._registry.register_feature(FeatureDefinition("price_change", "Price Net Change", "Price"), price_calc)
            self._registry.register_feature(FeatureDefinition("percentage_return", "Price Pct Return", "Price"), price_calc)
            self._registry.register_feature(FeatureDefinition("price_range", "Price Range", "Price"), price_calc)

            vol_calc = VolatilityFeatureCalculator()
            self._registry.register_feature(FeatureDefinition("rolling_volatility", "Rolling Annualized Volatility", "Volatility"), vol_calc)
            self._registry.register_feature(FeatureDefinition("range_expansion", "High Low Range Expansion", "Volatility"), vol_calc)
            self._registry.register_feature(FeatureDefinition("volatility_state", "Volatility State", "Volatility"), vol_calc)

            trend_calc = TrendFeatureCalculator()
            self._registry.register_feature(FeatureDefinition("directional_movement", "Directional Movement", "Trend"), trend_calc)
            self._registry.register_feature(FeatureDefinition("trend_strength_classification", "Trend Strength", "Trend"), trend_calc)

            stat_calc = StatisticalFeatureCalculator()
            self._registry.register_feature(FeatureDefinition("mean", "Arithmetic Mean", "Statistical"), stat_calc)
            self._registry.register_feature(FeatureDefinition("standard_deviation", "Standard Deviation", "Statistical"), stat_calc)
            self._registry.register_feature(FeatureDefinition("skewness", "Price Skewness", "Statistical"), stat_calc)

            pairs = self._registry.get_calculators_by_definition()

        # Keep track of which calculators we have executed to avoid double calculation
        executed_calculators = set()
        for definition, calculator in pairs:
            if calculator not in executed_calculators:
                executed_calculators.add(calculator)
                try:
                    calculated_values = calculator.calculate(data_points)
                    for val in calculated_values:
                        features_dict[val.FeatureName] = val
                except Exception as e:
                    raise ValidationException(
                        f"Validation Error: Calculator '{calculator.__class__.__name__}' failed: {str(e)}"
                    ) from e

        # Construct feature set
        return MarketFeatureSet(
            AssetId=asset_id,
            StartTime=start_time,
            EndTime=end_time,
            Features=features_dict,
            SourceDatasetInfo={"record_count": len(data_points)}
        )
