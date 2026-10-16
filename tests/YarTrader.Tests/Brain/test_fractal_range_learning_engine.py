import unittest

from src.Research.Brain.fractal_range_learning_engine import FractalRangeLearningEngine, _clean, _completed_times, _snapshot
from src.Research.Brain.fractal_nested_range_discovery import FractalNestedRangeDiscovery


def bars(tf_seconds=60, n=180, scale=1.0, drift=0.0):
    out=[]
    for i in range(n):
        center=100*scale + i*drift*scale + ((i%7)-3)*0.12*scale
        out.append({"time":1700000000+i*tf_seconds,"open":center,
                    "high":center+0.45*scale,"low":center-0.45*scale,
                    "close":center+(0.12 if i%2 else -0.08)*scale})
    return out


class TestFractalRangeLearningEngine(unittest.TestCase):
    def test_clean_sorts_and_deduplicates_without_fabricating(self):
        source=bars(n=12)
        clean=_clean(list(reversed(source))+[source[-1]])
        self.assertEqual(len(clean),12)
        self.assertEqual([x["time"] for x in clean],sorted(x["time"] for x in clean))

    def test_builds_pooled_dataset_across_all_timeframes(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8)
        data=engine.build_dataset({
            "M1":bars(60,n=80,scale=.01),
            "M5":bars(300,n=80,scale=.02),
            "H1":bars(3600,n=80,scale=.03),
            "D1":bars(86400,n=80,scale=.04),
        })
        self.assertGreater(data["sample_count"],0)
        self.assertEqual(set(x["timeframe"] for x in data["samples"]),{"M1","M5","H1","D1"})
        self.assertIn("context_MN1_present",data["feature_names"])
        self.assertIn("context_M1_present",data["feature_names"])
        self.assertIn("context_MN1_candidate_score",data["feature_names"])
        self.assertIn("context_H1_candidate_width_atr",data["feature_names"])
        self.assertIn("future bars only define offline labels",data["leakage_guard"])
        sample = data["samples"][0]
        self.assertGreater(sample["atr"], 0)
        self.assertGreater(sample["target_up_price"], sample["current_close"])
        self.assertLess(sample["target_down_price"], sample["current_close"])
        self.assertGreaterEqual(sample["bars_to_up_barrier"], 1)
        self.assertGreaterEqual(sample["bars_to_down_barrier"], 1)
        self.assertIn("swing_start_up_offset_atr", sample)
        self.assertIn("swing_target_down_atr", sample)
        self.assertGreaterEqual(sample["bars_to_swing_target_up"], sample["bars_to_swing_start_up"])

    def test_variable_range_features_do_not_change_when_future_bars_are_appended(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8,max_samples_per_tf=1000)
        source=bars(n=90)
        before=engine.build_dataset({"M1":source[:70]})
        after=engine.build_dataset({"M1":source[:90]})
        old_sample=next(s for s in before["samples"] if s["time"] == before["samples"][5]["time"])
        same_time=next(s for s in after["samples"] if s["time"] == old_sample["time"])
        for key in ("context_M1_candidate_duration_norm", "context_M1_candidate_width_atr",
                    "context_M1_candidate_score", "context_M1_candidate_efficiency",
                    "context_M1_candidate_displacement", "context_M1_candidate_position"):
            self.assertAlmostEqual(old_sample["features"][key], same_time["features"][key], places=10)

    def test_insufficient_data_does_not_fake_model_or_metrics(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8)
        result=engine.train_evaluate({"samples":[]},train_fraction=.7)
        self.assertEqual(result["status"],"INSUFFICIENT_DATA")
        self.assertFalse(result["model_trained"])

    def test_sampling_spans_full_history_and_uses_candle_close_time(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8,max_samples_per_tf=10)
        data=engine.build_dataset({"M1":bars(60,n=120)})
        samples=data["samples"]
        self.assertEqual(data["incomplete_tail_bars_dropped"]["M1"],1)
        self.assertEqual(data["bars_by_timeframe"]["M1"],119)
        self.assertEqual(len(samples),10)
        self.assertGreater(samples[-1]["time"],samples[0]["time"] + 80*60)
        self.assertGreater(samples[-1]["label_end_time"],samples[-1]["time"])

    def test_global_temporal_holdout_purges_overlapping_labels(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8)
        samples=[]
        for t in range(1,121):
            for tf in ("M1","H1"):
                samples.append({
                    "time":t*3600,
                    "label_end_time":t*3600+300,
                    "timeframe":tf,
                    "features":{},
                    "label":t%3,
                })
        result=engine.train_evaluate({"samples":samples},train_fraction=.7)
        self.assertIn(result["status"],("EVALUATED_OOS","INSUFFICIENT_DATA"))
        if result["status"]=="EVALUATED_OOS":
            metrics=result["metrics"]
            self.assertLess(metrics["train_time_range"][1],metrics["test_time_range"][0])
        bounded=engine.train_evaluate(
            {"samples":samples},train_fraction=.7,
            train_until=80*3600,test_until=100*3600,
        )
        if bounded["status"]=="EVALUATED_OOS":
            metrics=bounded["metrics"]
            self.assertGreaterEqual(metrics["test_time_range"][0],80*3600)
            self.assertLess(metrics["test_time_range"][1],100*3600)

    def test_atr_does_not_treat_session_gap_as_one_bar_true_range(self):
        source=[
            {"time":1000,"open":100.0,"high":101.0,"low":99.0,"close":100.0},
            {"time":1060,"open":100.0,"high":101.0,"low":99.0,"close":100.0},
            {"time":87400,"open":200.0,"high":201.0,"low":199.0,"close":200.0},
        ]
        snap=_snapshot(source,"M1",3)
        self.assertAlmostEqual(snap["range_atr"],51.0,places=6)

    def test_gap_crossing_samples_are_excluded_and_context_restarts(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8,max_samples_per_tf=1000)
        source=bars(n=160)
        gap_index=80
        for row in source[gap_index:]:
            row["time"] += 3600
            for key in ("open", "high", "low", "close"):
                row[key] += 100.0
        gap_open=source[gap_index]["time"]
        data=engine.build_dataset({"M1":source})
        self.assertEqual(data["version"],"fractal_range_learning_v5_session_gap_aware_simple_modes")
        self.assertEqual(data["gap_policy_seconds"]["M1"],90)
        self.assertTrue(data["gap_policy"].startswith("samples are rejected"))
        self.assertTrue(data["samples"])
        for sample in data["samples"]:
            if sample["time"] < gap_open:
                self.assertLess(sample["label_end_time"],gap_open)
        post_gap_time=source[gap_index + 15]["time"] + 60
        post_gap_sample=next(sample for sample in data["samples"] if sample["time"] == post_gap_time)
        self.assertEqual(post_gap_sample["features"]["context_M1_present"],1.0)
        self.assertLess(post_gap_sample["features"]["context_M1_candidate_width_atr"],10.0)

    def test_simple_feature_modes_are_explicit_and_keep_same_oos_split(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8)
        names=["range_atr","close_position","net_displacement","path_efficiency","timeframe_seconds_log",
               "context_M15_position","context_M15_range_atr","context_H1_position","context_H1_range_atr",
               "context_H4_position","context_H4_range_atr","context_D1_position","context_D1_range_atr",
               "context_M1_candidate_score"]
        samples=[]
        for i in range(180):
            features={name:float((i % 11) / 10) for name in names}
            samples.append({"time":i*60,"label_end_time":i*60+30,"timeframe":"M1",
                            "features":features,"label":i%3})
        dataset={"samples":samples,"feature_names":names}
        full=engine.train_evaluate(dataset,train_fraction=.7,feature_mode="full")
        simple=engine.train_evaluate(dataset,train_fraction=.7,feature_mode="simple")
        range_only=engine.train_evaluate(dataset,train_fraction=.7,feature_mode="range_only")
        self.assertEqual(full["status"],"EVALUATED_OOS")
        self.assertEqual(simple["status"],"EVALUATED_OOS")
        self.assertEqual(range_only["status"],"EVALUATED_OOS")
        self.assertEqual(full["test_samples"],simple["test_samples"])
        self.assertEqual(simple["test_samples"],range_only["test_samples"])
        self.assertEqual(full["feature_count"],len(names))
        self.assertEqual(simple["feature_count"],13)
        self.assertEqual(range_only["feature_count"],4)
        self.assertEqual(simple["feature_mode"],"simple")
        self.assertEqual(range_only["feature_mode"],"range_only")

    def test_unknown_feature_mode_is_rejected(self):
        engine=FractalRangeLearningEngine(window=16,horizon=3,min_bars=8)
        samples=[{"time":i,"label_end_time":i+1,"timeframe":"M1","features":{},"label":i%3}
                 for i in range(120)]
        with self.assertRaises(ValueError):
            engine.train_evaluate({"samples":samples,"feature_names":[]},feature_mode="magical")

    def test_monthly_candle_close_uses_next_calendar_month_open(self):
        rows=[
            {"time":1714521600,"open":1.0,"high":2.0,"low":1.0,"close":1.5},
            {"time":1717200000,"open":1.5,"high":2.0,"low":1.2,"close":1.8},
        ]
        completed=_completed_times("MN1",rows)
        self.assertEqual(completed[0],rows[1]["time"])
        self.assertNotEqual(completed[0],rows[0]["time"]+30*86400)

    def test_invalid_ohlc_rows_are_rejected(self):
        self.assertEqual(_clean([{"time":1,"open":10,"high":8,"low":9,"close":10}]),[])


if __name__=="__main__":
    unittest.main()
