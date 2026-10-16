"""Causal event study: XAUUSD M1 prior-range breakouts, gap-aware and chronological.
Research only: no order routing or live inference. Uses fixed historical OHLC barriers.
"""
import csv, json, math, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "runtime_logs" / "mt5_gold_history_full"
SOURCE = DATA / "M1.csv"
OUT = DATA / "xauusd_range_breakout_event_study_20261010.json"
MAX_GAP_SECONDS = 90
SAMPLE_STEP = 15
LOOKBACK = 24
ATR_LEN = 24
HORIZONS = (24, 48, 96)
BUFFER_ATR = 0.10
SEED_TRAIN_FRACTION = 0.50


def load_bars():
    rows = []
    with SOURCE.open("r", newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                row = (int(float(r["time"])), float(r["open"]), float(r["high"]),
                       float(r["low"]), float(r["close"]))
            except (ValueError, TypeError, KeyError):
                continue
            t, o, h, l, c = row
            if t > 0 and min(o, h, l, c) > 0 and h >= max(o, c, l) and l <= min(o, c, h):
                rows.append(row)
    rows.sort(key=lambda x: x[0])
    unique = {}
    for r in rows:
        unique[r[0]] = r
    return list(unique.values())


def summarize(rows, label):
    if not rows:
        return {"condition": label, "n": 0}
    result = {"condition": label, "n": len(rows)}
    for hz in HORIZONS:
        chosen = [r for r in rows if r["outcomes"][hz]["class"] != "not_hit"]
        up = sum(r["outcomes"][hz]["class"] == "up" for r in chosen)
        down = sum(r["outcomes"][hz]["class"] == "down" for r in chosen)
        tie = sum(r["outcomes"][hz]["class"] == "ambiguous" for r in rows)
        result[f"h{hz}"] = {
            "up_first_rate_all": up / len(rows),
            "down_first_rate_all": down / len(rows),
            "no_hit_rate": sum(r["outcomes"][hz]["class"] == "not_hit" for r in rows) / len(rows),
            "same_bar_ambiguous_rate": tie / len(rows),
            "resolved_directional_n": len(chosen),
            "up_share_given_resolved": up / len(chosen) if chosen else None,
            "median_bars_to_first_hit": float(np.median([r["outcomes"][hz]["bars"] for r in chosen])) if chosen else None,
        }
    return result


def summarize_symmetric(rows, label):
    if not rows:
        return {"condition": label, "n": 0}
    result = {"condition": label, "n": len(rows)}
    for hz in HORIZONS:
        outcomes = [r["symmetric"][hz] for r in rows]
        up = sum(x["class"] == "up" for x in outcomes)
        down = sum(x["class"] == "down" for x in outcomes)
        no_hit = sum(x["class"] == "not_hit" for x in outcomes)
        ambiguous = sum(x["class"] == "ambiguous" for x in outcomes)
        resolved = up + down
        result[f"h{hz}"] = {
            "up_first_rate_all": up / len(rows),
            "down_first_rate_all": down / len(rows),
            "no_hit_rate": no_hit / len(rows),
            "same_bar_ambiguous_rate": ambiguous / len(rows),
            "resolved_directional_n": resolved,
            "up_share_given_resolved": up / resolved if resolved else None,
            "median_bars_to_first_hit": float(np.median([x["bars"] for x in outcomes if x["class"] in ("up", "down")])) if resolved else None,
        }
    return result


def main():
    started = time.time()
    bars = load_bars()
    segments, cur = [], []
    for b in bars:
        if cur and b[0] - cur[-1][0] > MAX_GAP_SECONDS:
            if len(cur) > max(LOOKBACK, ATR_LEN) + max(HORIZONS) + 2:
                segments.append(cur)
            cur = []
        cur.append(b)
    if len(cur) > max(LOOKBACK, ATR_LEN) + max(HORIZONS) + 2:
        segments.append(cur)
    del bars

    samples = []
    for sid, seg in enumerate(segments):
        start = max(LOOKBACK, ATR_LEN)
        end = len(seg) - max(HORIZONS) - 1
        for i in range(start, end + 1, SAMPLE_STEP):
            c = seg[i][4]
            trs = []
            for j in range(i - ATR_LEN + 1, i + 1):
                pc = seg[j - 1][4]
                trs.append(max(seg[j][2] - seg[j][3], abs(seg[j][2] - pc), abs(seg[j][3] - pc)))
            atr = max(float(np.mean(trs)), 1e-9)
            prior = seg[i - LOOKBACK:i + 1]
            hi = max(x[2] for x in prior)
            lo = min(x[3] for x in prior)
            width = max(hi - lo, 1e-9)
            prior96 = seg[max(0, i - 96 + 1):i + 1]
            hi96, lo96 = max(x[2] for x in prior96), min(x[3] for x in prior96)
            width96 = max(hi96 - lo96, 1e-9)
            pos = (c - lo) / width
            compression = width / atr
            nested_ratio = width / width96
            outcomes, symmetric = {}, {}
            for hz in HORIZONS:
                first = None
                first_sym = None
                future = seg[i + 1:i + hz + 1]
                upper_range = hi + BUFFER_ATR * atr
                lower_range = lo - BUFFER_ATR * atr
                upper_sym = c + 2.0 * atr
                lower_sym = c - 2.0 * atr
                for k, b in enumerate(future, 1):
                    up_hit = b[2] >= upper_range
                    down_hit = b[3] <= lower_range
                    if up_hit and down_hit:
                        first = {"class": "ambiguous", "bars": k}
                    elif up_hit:
                        first = {"class": "up", "bars": k}
                    elif down_hit:
                        first = {"class": "down", "bars": k}
                    if first is not None:
                        break
                for k, b in enumerate(future, 1):
                    up_hit = b[2] >= upper_sym
                    down_hit = b[3] <= lower_sym
                    if up_hit and down_hit:
                        first_sym = {"class": "ambiguous", "bars": k}
                    elif up_hit:
                        first_sym = {"class": "up", "bars": k}
                    elif down_hit:
                        first_sym = {"class": "down", "bars": k}
                    if first_sym is not None:
                        break
                outcomes[hz] = first or {"class": "not_hit", "bars": None}
                symmetric[hz] = first_sym or {"class": "not_hit", "bars": None}
            samples.append({"time": seg[i][0], "segment": sid, "compression": compression,
                            "nested_ratio": nested_ratio, "position": pos,
                            "outcomes": outcomes, "symmetric": symmetric})
    samples.sort(key=lambda x: x["time"])
    if len(samples) < 1000:
        raise SystemExit(f"Insufficient samples: {len(samples)}")

    # Define compression threshold using only the earliest 50% of samples; freeze for all later data.
    seed_n = int(len(samples) * SEED_TRAIN_FRACTION)
    compression_cut = float(np.quantile([x["compression"] for x in samples[:seed_n]], 0.25))
    nested_cut = float(np.quantile([x["nested_ratio"] for x in samples[:seed_n]], 0.25))
    # Chronological three-way OOS summaries use the same fixed thresholds.
    thirds = [samples[:len(samples)//3], samples[len(samples)//3:2*len(samples)//3], samples[2*len(samples)//3:]]
    report = {
        "status": "RESEARCH_ONLY",
        "symbol": "XAUUSD", "timeframe": "M1",
        "source": str(SOURCE),
        "method": {
            "gap_split_seconds": MAX_GAP_SECONDS, "sample_step_bars": SAMPLE_STEP,
            "prior_range_lookback_bars": LOOKBACK, "atr_bars": ATR_LEN,
            "horizons_bars": list(HORIZONS), "break_buffer_atr": BUFFER_ATR,
            "upper_lower_barriers": "prior 24-bar high/low, expanded by 0.10 decision-time ATR; first high/low touch wins",
            "same_bar_both_sides": "ambiguous; not assigned direction",
            "compression_definition": "prior 24-bar high-low width / decision-time ATR",
            "nested_definition": "prior 24-bar width / prior 96-bar width",
            "symmetric_barrier_atr": 2.0,
            "thresholds_fit_on_first_half_only": True,
            "compression_q25_cut": compression_cut, "nested_ratio_q25_cut": nested_cut,
            "no_trade_execution": True
        },
        "data": {"segments": len(segments), "samples": len(samples),
                 "first_epoch": samples[0]["time"], "last_epoch": samples[-1]["time"]},
        "all_sample": summarize(samples, "all"),
        "symmetric_barrier_note": "Control outcome: first touch of symmetric +/-2.0 ATR barriers from decision close. This avoids the built-in distance advantage of being near one prior-range boundary.",
        "symmetric_all_sample": summarize_symmetric(samples, "all"),
        "symmetric_conditions": {
            "compressed_q25": summarize_symmetric([x for x in samples if x["compression"] <= compression_cut], "compressed_q25"),
            "not_compressed": summarize_symmetric([x for x in samples if x["compression"] > compression_cut], "not_compressed"),
            "nested_tight_q25": summarize_symmetric([x for x in samples if x["nested_ratio"] <= nested_cut], "nested_tight_q25"),
            "near_upper_edge": summarize_symmetric([x for x in samples if x["position"] >= 0.8], "near_upper_edge"),
            "near_lower_edge": summarize_symmetric([x for x in samples if x["position"] <= 0.2], "near_lower_edge"),
            "middle_range": summarize_symmetric([x for x in samples if 0.2 < x["position"] < 0.8], "middle_range")
        },
        "conditions": {
            "compressed_q25": summarize([x for x in samples if x["compression"] <= compression_cut], "compression <= first-half q25"),
            "not_compressed": summarize([x for x in samples if x["compression"] > compression_cut], "compression > first-half q25"),
            "nested_tight_q25": summarize([x for x in samples if x["nested_ratio"] <= nested_cut], "nested ratio <= first-half q25"),
            "near_upper_edge": summarize([x for x in samples if x["position"] >= 0.8], "close in upper 20% of prior range"),
            "near_lower_edge": summarize([x for x in samples if x["position"] <= 0.2], "close in lower 20% of prior range"),
            "middle_range": summarize([x for x in samples if 0.2 < x["position"] < 0.8], "close in middle 60% of prior range")
        },
        "chronological_thirds": []
    }
    for i, part in enumerate(thirds, 1):
        report["chronological_thirds"].append({
            "period": i, "n": len(part),
            "all": summarize(part, "all"),
            "symmetric_all": summarize_symmetric(part, "all"),
            "symmetric_compressed_q25": summarize_symmetric([x for x in part if x["compression"] <= compression_cut], "compressed_q25"),
            "symmetric_nested_tight_q25": summarize_symmetric([x for x in part if x["nested_ratio"] <= nested_cut], "nested_tight_q25"),
            "symmetric_near_upper_edge": summarize_symmetric([x for x in part if x["position"] >= 0.8], "near_upper_edge"),
            "symmetric_near_lower_edge": summarize_symmetric([x for x in part if x["position"] <= 0.2], "near_lower_edge"),
            "compressed_q25": summarize([x for x in part if x["compression"] <= compression_cut], "compressed_q25"),
            "nested_tight_q25": summarize([x for x in part if x["nested_ratio"] <= nested_cut], "nested_tight_q25"),
            "near_upper_edge": summarize([x for x in part if x["position"] >= 0.8], "near_upper_edge"),
            "near_lower_edge": summarize([x for x in part if x["position"] <= 0.2], "near_lower_edge")
        })
    report["elapsed_seconds"] = round(time.time() - started, 2)
    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUT), "data": report["data"], "method": report["method"],
                      "all_sample": report["all_sample"], "symmetric_all_sample": report["symmetric_all_sample"],
                      "symmetric_conditions": report["symmetric_conditions"],
                      "conditions": report["conditions"], "chronological_thirds": report["chronological_thirds"],
                      "elapsed_seconds": report["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
