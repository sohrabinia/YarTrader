from src.Research.Brain.multitimeframe_base_transition_engine import (
    build_hierarchy, detect_base_departures, label_exit_to_next_base
)


def _bars(n=80, start=2000.0):
    rows=[]
    p=start
    for i in range(n):
        # Deterministic quiet candles with occasional small oscillation.
        o=p
        c=p + (0.03 if i%2 else -0.02)
        rows.append({"time":1700000000+i*60,"open":o,"high":max(o,c)+0.08,
                     "low":min(o,c)-0.08,"close":c})
        p=c
    return rows


def test_detector_is_deterministic_and_returns_causal_metadata():
    bars=_bars()
    first=detect_base_departures(bars,"M1",scan_step=1)
    second=detect_base_departures(bars,"M1",scan_step=1)
    assert first == second
    for event in first:
        assert event["feature_cutoff_time"] == event["confirmation_time"]
        assert event["base_start_time"] <= event["base_end_time"] <= event["confirmation_time"]
        assert event["base_type"] in {"RBR","DBD","DBR","RBD"}


def test_hierarchy_only_counts_children_confirmed_before_parent_exit():
    parent={
        "event_id":"H4:100:RBR","timeframe":"H4","base_start_time":10,
        "base_end_time":90,"confirmation_time":100,"base_type":"RBR",
        "base_low":100.0,"base_high":110.0,"base_mid":105.0,"exit_direction":1
    }
    child={
        "event_id":"M15:80:RBR","timeframe":"M15","base_start_time":20,
        "base_end_time":70,"confirmation_time":80,"base_type":"RBR",
        "base_low":102.0,"base_high":106.0,"base_mid":104.0,"exit_direction":1
    }
    future_child=dict(child,event_id="M5:120:DBD",timeframe="M5",
                      confirmation_time=120,base_type="DBD",exit_direction=-1)
    result=build_hierarchy({"H4":[parent],"M15":[child],"M5":[future_child]})
    parent_row=next(x for x in result if x["event_id"]==parent["event_id"])
    assert parent_row["child_bases"]["M15"]["count"] == 1
    assert parent_row["child_alignment_count"] == 1
    assert parent_row["child_opposition_count"] == 0


def test_transition_labels_exclude_future_confirmed_target_base():
    bars=_bars(80,2000.0)
    event={
        "event_id":"M1:1700001800:RBR","timeframe":"M1","base_type":"RBR",
        "confirmation_index":30,"confirmation_time":bars[30]["time"],
        "base_high":2001.0,"base_low":1999.0,"base_mid":2000.0,"base_atr":1.0,
        "exit_direction":1
    }
    future_target={
        "event_id":"H1:future:DBD","timeframe":"H1","base_high":2005.0,"base_low":2003.0,
        "base_mid":2004.0,"confirmation_time":bars[40]["time"]
    }
    rows=label_exit_to_next_base({"M1":[event],"H1":[future_target]},{"M1":bars,"H1":bars},horizon_bars=24)
    assert len(rows)==1
    assert rows[0]["next_base_id"] is None
    assert rows[0]["label_mode"]=="OFFLINE_OUTCOME_ONLY"



def test_context_uses_only_fully_closed_higher_timeframe_candles():
    from src.Research.Brain.multitimeframe_base_transition_engine import attach_market_context
    base_time = 1700000000
    bars = []
    price = 2000.0
    for i in range(30):
        o = price
        c = price + (0.1 if i % 2 else -0.05)
        bars.append({"time":base_time+i*3600,"open":o,"high":max(o,c)+0.2,
                     "low":min(o,c)-0.2,"close":c})
        price = c
    event = {"event_id":"M5:test","confirmation_time":base_time+15*3600}
    events = {"M5":[event]}
    attach_market_context(events, {"H1":bars})
    h1 = event["market_context"]["H1"]
    assert h1["status"] == "AVAILABLE"
    # Candle opening at base_time + 15h is still open at this timestamp.
    assert h1["closed_bar_time"] == base_time+15*3600
    assert h1["closed_bar_time"] <= event["confirmation_time"]



def test_baseline_backtest_enters_next_bar_and_applies_explicit_cost_proxy():
    from src.Research.Brain.multitimeframe_base_transition_engine import simulate_departure_trades
    bars = []
    for i in range(60):
        p = 100.0
        bars.append({"time":1700000000+i*60,"open":p,"high":p+0.2,"low":p-0.2,"close":p+0.05})
    event = {
        "event_id":"M1:signal:RBR","timeframe":"M1","base_type":"RBR",
        "confirmation_index":30,"confirmation_time":bars[31]["time"],
        "base_low":98.0,"base_high":100.5,"base_mid":99.25,"base_atr":1.0,
        "exit_direction":1,
    }
    result = simulate_departure_trades({"M1":[event]},{"M1":bars},[],horizon_bars=24)
    stats = result["summary"]["M1"]["fixed_2R"]["overall"]
    assert stats["trades"] == 1
    assert stats["mean_net_R_proxy"] < stats["mean_gross_R"]
    assert result["configuration"]["entry"] == "next bar open after departure confirmation"
    assert "last_30pct" in result["summary"]["M1"]["fixed_2R"]["chronological_split"]
    assert result["summary"]["M1"]["wave_rider"]["overall"]["trades"] == 1
    assert result["configuration"]["wave_rider"]["fixed_profit_target"] is False
    assert next(x for x in result["summary"]["M1"]["wave_rider"]["by_base_type"].values() if x["trades"] == 1)["trades"] == 1



def test_closeback_on_first_retest_is_classified_as_failed_exit():
    from src.Research.Brain.multitimeframe_base_transition_engine import label_exit_to_next_base
    bars = []
    for i in range(70):
        bars.append({"time":1700000000+i*60,"open":101.2,"high":101.3,"low":101.1,"close":101.2})
    bars[31] = {"time":1700000000+31*60,"open":101.2,"high":101.4,"low":100.5,"close":100.8}
    event = {
        "event_id":"M1:closeback:RBD","timeframe":"M1","base_type":"RBD",
        "confirmation_index":30,"confirmation_time":bars[31]["time"],
        "base_low":100.0,"base_high":101.0,"base_mid":100.5,"base_atr":1.0,
        "exit_direction":1,
    }
    rows = label_exit_to_next_base({"M1":[event]},{"M1":bars},horizon_bars=24)
    assert rows[0]["origin_retest_bars"] == 1
    assert rows[0]["failed_exit_closeback_bars"] == 1
    assert rows[0]["first_transition"] == "failed_exit_closeback"



def test_corridor_pause_tracks_following_departure_direction():
    from src.Research.Brain.multitimeframe_base_transition_engine import label_exit_to_next_base
    bars = []
    for i in range(70):
        bars.append({"time":1700000000+i*60,"open":101.2,"high":101.3,"low":101.1,"close":101.2})
    bars[31] = {"time":1700000000+31*60,"open":101.2,"high":101.25,"low":101.0,"close":101.1}
    bars[32] = {"time":1700000000+32*60,"open":101.1,"high":101.2,"low":101.0,"close":101.1}
    bars[33] = {"time":1700000000+33*60,"open":101.1,"high":101.2,"low":101.0,"close":101.1}
    bars[34] = {"time":1700000000+34*60,"open":101.1,"high":101.2,"low":101.0,"close":101.1}
    bars[35] = {"time":1700000000+35*60,"open":101.1,"high":102.2,"low":101.0,"close":102.0}
    event = {
        "event_id":"M1:pause:RBR","timeframe":"M1","base_type":"RBR",
        "confirmation_index":30,"confirmation_time":bars[31]["time"],
        "base_low":98.0,"base_high":99.0,"base_mid":98.5,"base_atr":1.0,
        "exit_direction":1,
    }
    rows = label_exit_to_next_base({"M1":[event]},{"M1":bars},horizon_bars=24)
    assert rows[0]["corridor_pause_candidate"] is True
    assert rows[0]["corridor_pause_departure_direction"] == 1
    assert rows[0]["corridor_pause_departure_aligned"] is True
