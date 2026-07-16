import argparse
import sys
import time
from datetime import datetime, timedelta

from src.Data.MarketData.Models.models import MarketDataRequest
from src.Data.MarketData.Providers.mt5_provider import MetaTrader5MarketDataProvider
from src.Data.MarketData.Normalization.validator import MarketDataValidator
from src.Data.MarketData.Normalization.quality_checker import DataQualityChecker
from src.Research.MarketAnalysis.Services.services import FeatureExtractionResearchEngine, ResearchProcessor
from src.Research.MarketAnalysis.Models.models import ResearchRequest
from src.Research.MarketAnalysis.Repositories.repository import InMemoryResearchRepository


def main():
    parser = argparse.ArgumentParser(
        description="RG_V3 AI Autonomous Market Research Runtime Platform."
    )
    parser.add_argument("--asset", type=str, default="XAUUSD", help="Asset symbol to watch.")
    parser.add_argument("--timeframe", type=str, default="H1", help="Timeframe (e.g. M1, H1, D1).")
    parser.add_argument("--bars", type=int, default=10, help="Number of bars/candles to fetch.")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds.")
    parser.add_argument("--once", action="store_true", default=True, help="Run only one iteration and exit.")

    args = parser.parse_args()

    print("RG_V3 Research Runtime Started\n")

    # 1. Initialize MT5 Provider
    provider = MetaTrader5MarketDataProvider()
    if provider.initialize():
        print("MT5 Connection:\nSUCCESS\n")
    else:
        print("MT5 Connection:\nFAILED\n")
        sys.exit(1)

    print("Provider:\nMetaTrader5MarketDataProvider\n")
    print(f"Asset:\n{args.asset}\n")
    print(f"Timeframe:\n{args.timeframe}\n")

    # Create repositories and engines
    repo = InMemoryResearchRepository()
    base_engine = ResearchProcessor()
    pipeline_engine = FeatureExtractionResearchEngine(data_provider=provider, base_engine=base_engine)
    validator = MarketDataValidator()
    quality_checker = DataQualityChecker()

    last_processed_timestamp = None

    try:
        while True:
            # 2. Retrieve Market Data Context
            # Setup time range for number of bars requested
            end_time = datetime.now()
            # approximate start time depending on timeframe
            delta_map = {
                "M1": timedelta(minutes=args.bars),
                "M5": timedelta(minutes=args.bars * 5),
                "M15": timedelta(minutes=args.bars * 15),
                "M30": timedelta(minutes=args.bars * 30),
                "H1": timedelta(hours=args.bars),
                "H4": timedelta(hours=args.bars * 4),
                "D1": timedelta(days=args.bars),
            }
            start_time = end_time - delta_map.get(args.timeframe, timedelta(hours=args.bars))

            request = MarketDataRequest(
                Asset=args.asset,
                StartTime=start_time,
                EndTime=end_time,
                Timeframe=args.timeframe
            )

            # Retrieve rates
            response = provider.retrieve_market_data(request)
            points = response.DataPoints

            if not points:
                print("Market Data:\nEMPTY\n")
                if args.once:
                    break
                time.sleep(args.interval)
                continue

            latest_pt = points[-1]
            latest_ts = latest_pt.Timestamp

            # 3. Candle scheduler check to prevent duplicate run
            if last_processed_timestamp == latest_ts:
                # Same candle, skip processing
                if args.once:
                    break
                time.sleep(args.interval)
                continue

            print("Market Data:\nRECEIVED\n")

            # 4. Validation & Quality Checks
            if validator.validate_market_data(points):
                print("Validation:\nPASSED\n")
            else:
                print("Validation:\nFAILED\n")
                sys.exit(1)

            # Optional quality audit checks
            q_report = quality_checker.check_quality(points)
            if q_report.InvalidRecords > 0:
                print(f"[WARNING] Quality checker flagged {q_report.InvalidRecords} invalid data points.")

            # 5. Feature Extraction & Research
            print("Feature Extraction:\nCOMPLETED\n")

            research_req = ResearchRequest(
                Asset=args.asset,
                StartTime=start_time,
                EndTime=end_time,
                Context={"timeframe": args.timeframe}
            )

            research_result = pipeline_engine.analyze_market(research_req)
            print("Research:\nCOMPLETED\n")

            # 6. Store Result
            repo.store_research_result(research_result)
            print("Storage:\nSUCCESS\n")

            # Update scheduler state
            last_processed_timestamp = latest_ts

            if args.once:
                break
            time.sleep(args.interval)

    finally:
        provider.shutdown()


if __name__ == "__main__":
    main()
