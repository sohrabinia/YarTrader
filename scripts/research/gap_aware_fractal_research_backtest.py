"""Gap-aware chronological research backtest for XAUUSD M1 range features.
Uses historical MT5 candles only. No order, broker, or live execution integration.
"""
import csv, json, math, time
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"runtime_logs"/"mt5_gold_history_full"
OUT=DATA/"gap_aware_fractal_research_backtest_20261010.json"
SOURCE=DATA/"M1.csv"
SAMPLE_STEP=60
MAX_GAP_SECONDS=90
LOOKBACKS=(8,24,48,96)
HORIZONS=(24,48,96)
THRESHOLD_ATR=0.75
RNG=np.random.default_rng(20261010)

def load(path):
    rows=[]
    with path.open("r",newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                t=int(float(r["time"])); o=float(r["open"]); h=float(r["high"]); l=float(r["low"]); c=float(r["close"])
            except (ValueError,TypeError,KeyError): continue
            if t>0 and min(o,h,l,c)>0 and h>=max(o,c,l) and l<=min(o,c,h):
                rows.append((t,o,h,l,c))
    rows.sort(key=lambda x:x[0])
    dedup={}
    for r in rows: dedup[r[0]]=r
    return list(dedup.values())

def feature_for(seg,i):
    # Only bars at or before decision index i are read.
    t,o,h,l,c=seg[i]
    out={}
    prev=seg[max(0,i-1)][4]
    trs=[]
    for j in range(max(0,i-23),i+1):
        _,oo,hh,ll,cc=seg[j]
        pc=seg[j-1][4] if j else cc
        trs.append(max(hh-ll,abs(hh-pc),abs(ll-pc)))
    atr=float(np.mean(trs)) if trs else max(h-l,1e-9)
    atr=max(atr,1e-9)
    out["atr_pct"]=atr/max(c,1e-9)
    rets=[]
    for j in range(max(1,i-96),i+1):
        rets.append(math.log(seg[j][4]/seg[j-1][4]))
    for lag in (1,2,4,8,16,32):
        out[f"ret_{lag}"]=math.log(c/seg[max(0,i-lag)][4]) if i>=lag else 0.0
    if rets:
        ar=np.abs(rets)
        out["ret_sd_24"]=float(np.std(rets[-24:])) if len(rets)>=2 else 0.0
        out["ret_sd_96"]=float(np.std(rets)) if len(rets)>=2 else 0.0
        out["absret_mean_8"]=float(np.mean(ar[-8:]))
        out["absret_mean_24"]=float(np.mean(ar[-24:]))
        out["absret_mean_96"]=float(np.mean(ar))
        out["vol_cluster_ratio"]=out["absret_mean_8"]/(out["absret_mean_96"]+1e-12)
    else:
        for k in ("ret_sd_24","ret_sd_96","absret_mean_8","absret_mean_24","absret_mean_96","vol_cluster_ratio"): out[k]=0.0
    widths={}
    for n in LOOKBACKS:
        start=max(0,i-n+1); w=seg[start:i+1]
        hi=max(x[2] for x in w); lo=min(x[3] for x in w); width=max(hi-lo,1e-9)
        closes=[x[4] for x in w]
        path=sum(abs(closes[k]-closes[k-1]) for k in range(1,len(closes)))
        displacement=closes[-1]-closes[0]
        widths[n]=(hi,lo,width)
        out[f"range_width_atr_{n}"]=width/atr
        out[f"range_position_{n}"]=(c-lo)/width
        out[f"path_efficiency_{n}"]=abs(displacement)/(path+1e-12)
        out[f"net_displacement_atr_{n}"]=displacement/atr
        out[f"range_width_pct_{n}"]=width/max(c,1e-9)
        out[f"close_change_{n}"]=math.log(c/max(closes[0],1e-9))
    for small,big in ((8,24),(24,48),(48,96),(8,48),(8,96),(24,96)):
        out[f"nested_width_ratio_{small}_{big}"]=widths[small][2]/(widths[big][2]+1e-12)
        out[f"nested_containment_{small}_{big}"]=float(widths[big][0]>=widths[small][0] and widths[big][1]<=widths[small][1])
    out["bar_body_atr"]=abs(c-o)/atr
    out["upper_wick_atr"]=(h-max(o,c))/atr
    out["lower_wick_atr"]=(min(o,c)-l)/atr
    out["close_location_bar"]=(c-l)/max(h-l,1e-9)
    out["gap_from_prev_atr"]=(o-prev)/atr
    return out,atr

def metrics_reg(y,pred,baseline):
    mae=float(np.mean(np.abs(y-pred))); bmae=float(np.mean(np.abs(y-baseline)))
    return {"model_mae":mae,"median_baseline_mae":bmae,
            "mae_improvement_pct":float(100*(bmae-mae)/max(bmae,1e-12)),
            "model_rmse":float(np.sqrt(np.mean((y-pred)**2))),
            "target_mean":float(np.mean(y)),"prediction_mean":float(np.mean(pred))}

def fit_classifier(train_x,test_x,ytr,yte):
    mean=train_x.mean(axis=0); scale=train_x.std(axis=0); scale[scale<1e-9]=1.0
    a=np.clip((train_x-mean)/scale,-10,10); b=np.clip((test_x-mean)/scale,-10,10)
    classes=np.asarray(sorted(set(ytr.tolist())),dtype=int)
    class_index={int(c):i for i,c in enumerate(classes)}
    yidx=np.asarray([class_index[int(v)] for v in ytr],dtype=int)
    onehot=np.eye(len(classes))[yidx]
    weights=np.zeros((a.shape[1],len(classes))); bias=np.zeros(len(classes))
    for epoch in range(100):
        logits=np.clip(a@weights+bias,-30,30); logits-=logits.max(axis=1,keepdims=True)
        exp=np.exp(logits); p=exp/exp.sum(axis=1,keepdims=True)
        error=(p-onehot)/len(ytr); lr=0.12/(1.0+epoch*0.02)
        weights-=lr*(a.T@error+0.01*weights); bias-=lr*error.sum(axis=0)
    logits=np.clip(b@weights+bias,-30,30); logits-=logits.max(axis=1,keepdims=True)
    probs=np.exp(logits); probs/=probs.sum(axis=1,keepdims=True)
    pred=classes[np.argmax(probs,axis=1)]
    acc=float(np.mean(pred==yte))
    recalls=[float(np.mean(pred[yte==c]==c)) for c in sorted(set(yte.tolist())) if np.any(yte==c)]
    majority=int(np.bincount(ytr,minlength=3).argmax())
    mapped={int(c):i for i,c in enumerate(classes)}
    loss=float(-np.log(np.maximum(probs[np.arange(len(yte)),[mapped[int(v)] for v in yte]],1e-12)).mean()) if all(int(v) in mapped for v in yte) else None
    return {"accuracy":acc,"balanced_accuracy":float(np.mean(recalls)),"log_loss":loss,
      "majority_baseline_accuracy":float(np.mean(yte==majority)),"majority_class_train":majority,
      "test_class_counts":{str(k):int(np.sum(yte==k)) for k in range(3)},
      "train_class_counts":{str(k):int(np.sum(ytr==k)) for k in range(3)}}

def main():
    started=time.time()
    bars=load(SOURCE)
    if len(bars)<10000: raise SystemExit(f"Insufficient M1 history: {len(bars)}")
    # Split into uninterrupted M1 sequences; never build features/labels across session gaps.
    segments=[]; cur=[]
    for b in bars:
        if cur and b[0]-cur[-1][0]>MAX_GAP_SECONDS:
            if len(cur)>=max(LOOKBACKS)+max(HORIZONS)+2: segments.append(cur)
            cur=[]
        cur.append(b)
    if len(cur)>=max(LOOKBACKS)+max(HORIZONS)+2: segments.append(cur)
    del bars
    samples=[]; skipped_gap=0
    for si,seg in enumerate(segments):
        # Sample at fixed stride but align within each contiguous segment.
        first=max(LOOKBACKS)-1
        last=len(seg)-max(HORIZONS)-1
        for i in range(first,last+1,SAMPLE_STEP):
            f,atr=feature_for(seg,i)
            future=seg[i+1:i+1+max(HORIZONS)]
            if len(future)<max(HORIZONS): continue
            labels={}
            for hz in HORIZONS:
                fut=future[:hz]
                labels[f"up_{hz}_atr"]=(max(x[2] for x in fut)-seg[i][4])/atr
                labels[f"down_{hz}_atr"]=(seg[i][4]-min(x[3] for x in fut))/atr
            # Retain close-direction class for audit, but train the primary classifier on first barrier passage.
            future_return=(future[23][4]-seg[i][4])/atr
            if future_return >= 0.25: close_cls=1
            elif future_return <= -0.25: close_cls=0
            else: close_cls=2
            # First passage times for upper/lower barriers, censored at horizon+1.
            for side in ("up","down"):
                target=THRESHOLD_ATR*atr; hit=HORIZONS[0]+1
                for k,b in enumerate(future[:HORIZONS[0]],1):
                    crossed=(b[2]-seg[i][4]>=target) if side=="up" else (seg[i][4]-b[3]>=target)
                    if crossed:
                        hit=k; break
                labels[f"time_{side}_24"]=hit
            up_t=labels["time_up_24"]; down_t=labels["time_down_24"]
            if up_t < down_t and up_t <= HORIZONS[0]: cls=1
            elif down_t < up_t and down_t <= HORIZONS[0]: cls=0
            else: cls=2  # both hit same bar, or neither hit within horizon
            samples.append({"time":seg[i][0],"segment":si,"features":f,"labels":labels,
                            "class":cls,"close_class":close_cls})
    if len(samples)<1000: raise SystemExit(f"Insufficient valid samples after gap filtering: {len(samples)}")
    samples.sort(key=lambda x:x["time"])
    # Strict chronological 70/30 split, purging every training label whose horizon crosses cutoff.
    cut=samples[int(len(samples)*0.70)]["time"]
    train=[s for s in samples if s["time"]<cut and s["time"]+max(HORIZONS)*60<=cut]
    test=[s for s in samples if s["time"]>=cut]
    feat_names=sorted(samples[0]["features"])
    Xtr=np.asarray([[s["features"][k] for k in feat_names] for s in train],dtype=float)
    Xte=np.asarray([[s["features"][k] for k in feat_names] for s in test],dtype=float)
    range_names=[k for k in feat_names if k.startswith(("range_","nested_","path_efficiency_","net_displacement_","close_change_"))]
    nonrange_names=[k for k in feat_names if k not in range_names]
    range_idx=[feat_names.index(k) for k in range_names]
    nonrange_idx=[feat_names.index(k) for k in nonrange_names]
    Xtr_raw=Xtr.copy(); Xte_raw=Xte.copy()
    report={"status":"RESEARCH_ONLY","symbol":"XAUUSD","timeframe":"M1","source":str(SOURCE),
      "configuration":{"sample_step_bars":SAMPLE_STEP,"max_gap_seconds":MAX_GAP_SECONDS,"lookbacks":LOOKBACKS,
       "horizons_bars":HORIZONS,"direction_threshold_atr":THRESHOLD_ATR,"primary_class_label":"first upper/lower barrier to cross within 24 bars; same-bar tie or no hit is ambiguous","split":"chronological 70/30",
       "purge":"train sample decision time + max horizon duration must not cross cutoff"},
      "data":{"valid_segments":len(segments),"samples":len(samples),"train_samples":len(train),"test_samples":len(test),
       "cutoff_epoch":cut,"first_sample_epoch":samples[0]["time"],"last_sample_epoch":samples[-1]["time"],
       "source_rows_note":"Full M1 CSV loaded, duplicate timestamps deduplicated, sequences split when timestamp gap exceeds 90 seconds."},
      "feature_names":feat_names,"range_feature_names":range_names,"nonrange_feature_names":nonrange_names,
      "numeric_targets":{},"numeric_targets_nonrange_baseline":{},"direction_classifier":{},"safety":"No orders; no live inference; no production model replacement."}
    mean=Xtr.mean(axis=0); scale=Xtr.std(axis=0); scale[scale<1e-9]=1.0
    Xtr=np.clip((Xtr-mean)/scale,-10,10); Xte=np.clip((Xte-mean)/scale,-10,10)
    for hz in HORIZONS:
        for side in ("up","down"):
            name=f"{side}_excursion_{hz}_bars_atr"
            ytr=np.asarray([s["labels"][f"{side}_{hz}_atr"] for s in train],dtype=float)
            yte=np.asarray([s["labels"][f"{side}_{hz}_atr"] for s in test],dtype=float)
            design=np.column_stack([np.ones(len(Xtr)),Xtr])
            design_test=np.column_stack([np.ones(len(Xte)),Xte])
            penalty=np.eye(design.shape[1])*100.0; penalty[0,0]=0.0
            coef=np.linalg.solve(design.T@design+penalty,design.T@ytr)
            pred=design_test@coef
            baseline=np.full(len(yte),float(np.median(ytr)))
            report["numeric_targets"][name]=metrics_reg(yte,pred,baseline)
            bxtr=Xtr_raw[:,nonrange_idx]; bxte=Xte_raw[:,nonrange_idx]
            bm=bxtr.mean(axis=0); bs=bxtr.std(axis=0); bs[bs<1e-9]=1.0
            bxtr=np.clip((bxtr-bm)/bs,-10,10); bxte=np.clip((bxte-bm)/bs,-10,10)
            bd=np.column_stack([np.ones(len(bxtr)),bxtr]); bdt=np.column_stack([np.ones(len(bxte)),bxte])
            bp=np.eye(bd.shape[1])*100.0; bp[0,0]=0.0
            bc=np.linalg.solve(bd.T@bd+bp,bd.T@ytr)
            report["numeric_targets_nonrange_baseline"][name]=metrics_reg(yte,bdt@bc,baseline)
    ytr=np.asarray([s["class"] for s in train],dtype=int); yte=np.asarray([s["class"] for s in test],dtype=int)
    all_result=fit_classifier(Xtr_raw,Xte_raw,ytr,yte)
    range_result=fit_classifier(Xtr_raw[:,range_idx],Xte_raw[:,range_idx],ytr,yte)
    nonrange_result=fit_classifier(Xtr_raw[:,nonrange_idx],Xte_raw[:,nonrange_idx],ytr,yte)
    report["direction_classifier"]={"all_features":all_result,"range_features_only":range_result,
      "nonrange_baseline_features":nonrange_result,
      "interpretation":"All comparisons use the same chronological OOS rows; a useful range signal should beat both the majority baseline and non-range features."}
    # Expanding-window walk-forward folds: train 50/65/80%, test the next 15%, with label purge.
    ordered=[s["time"] for s in samples]
    wf=[]
    for fold,(train_frac,test_frac) in enumerate(((0.50,0.65),(0.65,0.80),(0.80,0.95)),1):
        train_cut=ordered[min(len(ordered)-1,int((len(ordered)-1)*train_frac))]
        test_cut=ordered[min(len(ordered)-1,int((len(ordered)-1)*test_frac))]
        tr=[s for s in samples if s["time"]<train_cut and s["time"]+max(HORIZONS)*60<=train_cut]
        te=[s for s in samples if train_cut<=s["time"]<test_cut]
        if len(tr)<1000 or len(te)<500:
            wf.append({"fold":fold,"status":"INSUFFICIENT_DATA","train_samples":len(tr),"test_samples":len(te)})
            continue
        ytrf=np.asarray([s["class"] for s in tr],dtype=int); ytef=np.asarray([s["class"] for s in te],dtype=int)
        xtrf=np.asarray([[s["features"][k] for k in feat_names] for s in tr],dtype=float)
        xtef=np.asarray([[s["features"][k] for k in feat_names] for s in te],dtype=float)
        allf=fit_classifier(xtrf,xtef,ytrf,ytef)
        nrtr=np.asarray([[s["features"][k] for k in nonrange_names] for s in tr],dtype=float)
        nrte=np.asarray([[s["features"][k] for k in nonrange_names] for s in te],dtype=float)
        nrf=fit_classifier(nrtr,nrte,ytrf,ytef)
        wf.append({"fold":fold,"status":"EVALUATED","train_samples":len(tr),"test_samples":len(te),
          "train_cut_epoch":train_cut,"test_cut_epoch":test_cut,"all_features":allf,"nonrange_baseline_features":nrf})
    report["walk_forward"]=wf
    report["elapsed_seconds"]=round(time.time()-started,2)
    OUT.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"output":str(OUT),"data":report["data"],"direction_classifier":report["direction_classifier"],
      "numeric_targets":report["numeric_targets"],"elapsed_seconds":report["elapsed_seconds"]},indent=2))

if __name__=="__main__": main()
