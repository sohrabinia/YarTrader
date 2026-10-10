"""Train/evaluate the pooled fractal range model from an existing MT4 SQLite dataset."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.Application.Backtesting.historical_dataset import HistoricalDataset
from src.Research.Brain.fractal_range_learning_engine import FractalRangeLearningEngine, TIMEFRAMES


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--window",type=int,default=32)
    p.add_argument("--horizon",type=int,default=12)
    p.add_argument("--move-threshold-atr",type=float,default=1.0)
    p.add_argument("--train-fraction",type=float,default=.70)
    a=p.parse_args()
    source=Path(a.dataset)
    if not source.is_file():
        raise SystemExit(f"Dataset does not exist: {source}")
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    candles={}
    with HistoricalDataset(source) as db:
        manifest=db.manifest()
        for tf in TIMEFRAMES:
            first,last,count=db.first_last(tf)
            if count and first is not None and last is not None:
                candles[tf]=list(db.range(tf,first,last))
    engine=FractalRangeLearningEngine(window=a.window,horizon=a.horizon,
                                      move_threshold_atr=a.move_threshold_atr)
    data=engine.build_dataset(candles)
    result=engine.train_evaluate(data,a.train_fraction)
    model=result.pop("model",None)
    summary={k:v for k,v in data.items() if k!="samples"}
    summary["sample_counts_by_timeframe"]={tf:sum(s["timeframe"]==tf for s in data["samples"]) for tf in data["timeframes"]}
    (out/"dataset_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    report={"dataset_path":str(source.resolve()),"manifest":manifest,"dataset":summary,
            "evaluation":result,"safety":"RESEARCH_ONLY_NOT_CONNECTED_TO_ORDER_EXECUTION"}
    if model is not None:
        import numpy as np
        np.savez_compressed(out/"fractal_range_model.npz",weights=model["weights"],bias=model["bias"],
                            mean=model["mean"],scale=model["scale"],classes=model["classes"])
        (out/"model_features.json").write_text(json.dumps({"feature_names":model["feature_names"],
            "version":engine.VERSION,"label_definition":data["label_definition"]},indent=2),encoding="utf-8")
        report["model_artifact"]="fractal_range_model.npz"
    (out/"evaluation_report.json").write_text(json.dumps(report,indent=2,default=str),encoding="utf-8")
    print(json.dumps({"status":result.get("status"),"samples":data["sample_count"],
                      "timeframes":data["timeframes"],"output":str(out.resolve()),
                      "metrics":result.get("metrics",{})},indent=2,default=str))


if __name__=="__main__":
    main()
