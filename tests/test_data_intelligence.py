import unittest
from datetime import datetime, timedelta
from src.Data.MarketData.Models.models import MarketDataPoint, MarketDataRequest, MarketDataSourceInfo
from src.Data.MarketData.Providers.providers import MetaTrader5Provider, ExchangeProvider, FileImportProvider
from src.Data.MarketData.Normalization.normalization import MarketDataNormalizer
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Data.MarketData.Normalization.quality_checker import DataQualityChecker
from src.Data.HistoricalData.Repository.repository import HistoricalDataRepository

class TestDataIntelligence(unittest.TestCase):
    def test_data_modules_imports(self):
        """Verify that all Data Intelligence classes are successfully imported and exist."""
        self.assertIsNotNone(MetaTrader5Provider)
        self.assertIsNotNone(ExchangeProvider)
        self.assertIsNotNone(FileImportProvider)
        self.assertIsNotNone(MarketDataNormalizer)
        self.assertIsNotNone(MarketDataValidator)
        self.assertIsNotNone(DataQualityChecker)
        self.assertIsNotNone(HistoricalDataRepository)

    def test_market_data_request_response_models(self):
        """Verify market data request, response, and source info instantiation and properties."""
        now = datetime.now()
        req = MarketDataRequest(
            Asset="BTCUSD",
            StartTime=now - timedelta(days=1),
            EndTime=now,
            Timeframe="H1"
        )
        self.assertEqual(req.asset, "BTCUSD")
        self.assertEqual(req.timeframe, "H1")

        source = MarketDataSourceInfo(
            ProviderName="MetaTrader5",
            Version="5.0.0",
            DataType="OHLCV"
        )
        self.assertEqual(source.provider_name, "MetaTrader5")
        self.assertEqual(source.data_type, "OHLCV")

    def test_market_data_normalization(self):
        """Test standardizing diverse third-party external payloads."""
        normalizer = MarketDataNormalizer()

        # 1. Standard dictionary single bar
        external_bar = {
            "timestamp": "2026-03-06T12:00:00",
            "open": 101.5,
            "high": 103.0,
            "low": 100.5,
            "close": 102.0,
            "volume": 25000.0
        }

        normalized_list = normalizer.normalize_external_data(external_bar, "AAPL")
        self.assertEqual(len(normalized_list), 1)
        pt = normalized_list[0]
        self.assertEqual(pt.AssetId, "AAPL")
        self.assertEqual(pt.Open, 101.5)
        self.assertEqual(pt.High, 103.0)
        self.assertEqual(pt.Low, 100.5)
        self.assertEqual(pt.Close, 102.0)
        self.assertEqual(pt.Volume, 25000.0)
        self.assertEqual(pt.Timestamp, datetime.fromisoformat("2026-03-06T12:00:00"))

        # 2. Raw keys (short forms like o, h, l, c, v, t)
        short_bar = {
            "t": 1772841600,  # Epoch timestamp
            "o": 50.0,
            "h": 52.0,
            "l": 49.0,
            "c": 51.5,
            "v": 1000.0
        }
        normalized_short = normalizer.normalize_external_data(short_bar, "MSFT")
        self.assertEqual(len(normalized_short), 1)
        pt_short = normalized_short[0]
        self.assertEqual(pt_short.AssetId, "MSFT")
        self.assertEqual(pt_short.Open, 50.0)
        self.assertEqual(pt_short.High, 52.0)
        self.assertEqual(pt_short.Low, 49.0)
        self.assertEqual(pt_short.Close, 51.5)
        self.assertEqual(pt_short.Volume, 1000.0)
        self.assertEqual(pt_short.Timestamp, datetime.fromtimestamp(1772841600))

    def test_market_data_validation(self):
        """Test validation of price logical limits, volume non-negativity, and high/low relationships."""
        validator = MarketDataValidator()
        now = datetime.now()

        # Valid point
        valid_point = MarketDataPoint(
            AssetId="EURUSD",
            Timestamp=now,
            Open=1.0850,
            High=1.0900,
            Low=1.0800,
            Close=1.0880,
            Volume=50000.0
        )
        self.assertTrue(validator.validate_single_point(valid_point))

        # Invalid point: High is lower than Close
        invalid_high = MarketDataPoint(
            AssetId="EURUSD",
            Timestamp=now,
            Open=1.0850,
            High=1.0870,  # lower than Close of 1.0880
            Low=1.0800,
            Close=1.0880,
            Volume=50000.0
        )
        self.assertFalse(validator.validate_single_point(invalid_high))

        # Invalid point: Low is higher than Open
        invalid_low = MarketDataPoint(
            AssetId="EURUSD",
            Timestamp=now,
            Open=1.0850,
            High=1.0900,
            Low=1.0860,  # higher than Open of 1.0850
            Close=1.0880,
            Volume=50000.0
        )
        self.assertFalse(validator.validate_single_point(invalid_low))

        # Invalid point: Negative prices
        negative_price = MarketDataPoint(
            AssetId="EURUSD",
            Timestamp=now,
            Open=-1.0850,
            High=1.0900,
            Low=1.0800,
            Close=1.0880,
            Volume=50000.0
        )
        self.assertFalse(validator.validate_single_point(negative_price))

    def test_data_quality_checking(self):
        """Verify Quality Audits, record compliance checks, and warning logs."""
        checker = DataQualityChecker()
        now = datetime.now()

        points = [
            # Valid
            MarketDataPoint("AAPL", now, 150.0, 155.0, 149.0, 152.0, 10000.0),
            # Invalid (High < Close)
            MarketDataPoint("AAPL", now, 150.0, 151.0, 149.0, 152.0, 10000.0),
            # Valid but Warning (Zero volume)
            MarketDataPoint("AAPL", now, 150.0, 155.0, 149.0, 152.0, 0.0),
        ]

        report = checker.check_quality(points)
        self.assertEqual(report.total_records, 3)
        self.assertEqual(report.valid_records, 2)
        self.assertEqual(report.invalid_records, 1)
        self.assertTrue(len(report.warnings) >= 2)

    def test_historical_repository(self):
        """Test saving and retrieving data points via HistoricalDataRepository."""
        repo = HistoricalDataRepository()
        now = datetime.now()

        pts = [
            MarketDataPoint("BTCUSD", now - timedelta(hours=2), 60000.0, 61000.0, 59900.0, 60500.0, 1.5),
            MarketDataPoint("BTCUSD", now - timedelta(hours=1), 60500.0, 62000.0, 60400.0, 61800.0, 2.1),
            MarketDataPoint("ETHUSD", now, 3500.0, 3600.0, 3490.0, 3550.0, 15.0),
        ]

        repo.store_historical_data(pts)

        # Query BTCUSD historical data
        request = MarketDataRequest(
            Asset="BTCUSD",
            StartTime=now - timedelta(hours=3),
            EndTime=now,
            Timeframe="H1"
        )
        btc_pts = repo.retrieve_historical_data(request)
        self.assertEqual(len(btc_pts), 2)
        self.assertEqual(btc_pts[0].Close, 60500.0)
        self.assertEqual(btc_pts[1].Close, 61800.0)
