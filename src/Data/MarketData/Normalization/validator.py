from datetime import datetime
from typing import List
from src.Data.MarketData.Interfaces.interfaces import IMarketDataValidator
from src.Data.MarketData.Models.models import MarketDataPoint

class MarketDataValidator(IMarketDataValidator):
    """
    Validates structural correctness of market data records to guarantee mathematical consistency.
    """
    def validate_market_data(self, points: List[MarketDataPoint]) -> bool:
        """Returns True if every point in the list completely conforms to valid price logic."""
        if not points:
            return False

        for pt in points:
            if not self.validate_single_point(pt):
                return False
        return True

    def validate_single_point(self, pt: MarketDataPoint) -> bool:
        """Helper to check individual point constraints."""
        # 1. Price fields must be positive
        if pt.Open <= 0 or pt.High <= 0 or pt.Low <= 0 or pt.Close <= 0:
            return False

        # 2. Volume must be non-negative
        if pt.Volume < 0:
            return False

        # 3. High must be mathematically the highest price of the bar
        if pt.High < pt.Open or pt.High < pt.Close or pt.High < pt.Low:
            return False

        # 4. Low must be mathematically the lowest price of the bar
        if pt.Low > pt.Open or pt.Low > pt.Close or pt.Low > pt.High:
            return False

        # 5. Timestamp should not be in the future (plus a tiny safety margin of 60 seconds)
        if pt.Timestamp.timestamp() > datetime.now().timestamp() + 60:
            return False

        return True
