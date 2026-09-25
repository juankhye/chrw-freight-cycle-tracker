"""Refresh data/auto.json for the CHRW Freight Cycle Tracker.

Sources (all free, no API key):
  FRED  - Cass Freight Index shipments / expenditures, truckload PPI,
          truck-transportation employment, on-highway diesel price.
  Yahoo - weekly share prices for CHRW and peers.

Manual series (DAT, tender rejections, Class 8, FMCSA, CHRW quarterly KPIs)
live in data/manual.json and are edited by hand.
"""
import json, csv, io, sys, urllib.request, datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "auto.json"

FRED = {
    "cass_shipments":  "FRGSHPUSM649NCIS",   # Cass Freight Index: Shipments (index)
    "cass_expend":     "FRGEXPUSM649NCIS",   # Cass Freight Index: Expenditures (index)
    "tl_ppi":          "PCU484121484121",    # PPI: General freight trucking, long-distance truckload
    "truck_jobs":      "CES4348400001",      # Employment: truck transportation (thousands)
    "diesel":          "GASDESW",            # US on-highway diesel, $/gal, weekly
}
YAHOO = {"CHRW": "CHRW", "KNX": "KNX", "SPY": "SPY"}

UA = {"User-Agent": "curl/8.4.0"}  # FRED stalls on browser-like UAs from some networks

BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}

def get(url):
    """Fetch text over HTTPS. Tries urllib first, falls back to curl (some
    Windows/proxy setups time out in Python but work in curl).
    FRED stalls on browser-like user agents from some networks, Yahoo rejects
    non-browser ones, so pick the header by host."""
    hdr = BROWSER_UA if "yahoo" in url else UA
    try:
        req = urllib.request.Request(url, headers=hdr)
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8")
    except Exception as e:
        import subprocess
        out = subprocess.run(["curl", "-sL", "-m", "60", "-A", hdr["User-Agent"], url], capture_output=True, text=True, encoding="utf-8")
        if out.returncode == 0 and out.stdout:
            return out.stdout
        raise RuntimeError(f"urllib failed ({e}); curl rc={out.returncode}")

def fred(series):
    txt = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}")
    rows = list(csv.reader(io.StringIO(txt)))[1:]
    d, v = [], []
    for date, val in rows:
        if val in (".", ""):
            continue
        d.append(date); v.append(float(val))
    return {"dates": d, "values": v}

def yoy(dates, values, lag):
    """Year-over-year % change for a regular series with `lag` observations per year."""
    out = []
    for i in range(len(values)):
        if i < lag or values[i-lag] in (None, 0):
            out.append(None)
        else:
            out.append(round((values[i] / values[i-lag] - 1) * 100, 2))
    return out

def yahoo_weekly(sym):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=10y&interval=1wk"
    d = json.loads(get(url))["chart"]["result"][0]
    ts = d["timestamp"]; q = d["indicators"]["quote"][0]
    dates, close = [], []
    for t, c in zip(ts, q["close"]):
        if c is None:
            continue
        dates.append(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")); close.append(round(c, 2))
    meta = d.get("meta", {})
    return {"dates": dates, "close": close, "last": meta.get("regularMarketPrice"), "last_time": meta.get("regularMarketTime")}

def main():
    out = {"generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "fred": {}, "prices": {}}
    for k, s in FRED.items():
        try:
            ser = fred(s)
            lag = 52 if k == "diesel" else 12
            ser["yoy"] = yoy(ser["dates"], ser["values"], lag)
            ser["series_id"] = s
            out["fred"][k] = ser
            print(f"FRED {s}: {len(ser['values'])} obs, last {ser['dates'][-1]} = {ser['values'][-1]}")
        except Exception as e:
            print(f"FRED {s} FAILED: {e}", file=sys.stderr)
    # Derived: Cass expenditures per shipment = implied cost per shipment (rate proxy)
    try:
        s, e = out["fred"]["cass_shipments"], out["fred"]["cass_expend"]
        common = [d for d in s["dates"] if d in set(e["dates"])]
        si = {d: v for d, v in zip(s["dates"], s["values"])}; ei = {d: v for d, v in zip(e["dates"], e["values"])}
        vals = [round(ei[d] / si[d], 4) for d in common]
        out["fred"]["cass_rate_proxy"] = {"dates": common, "values": vals, "yoy": yoy(common, vals, 12), "series_id": "FRGEXPUSM649NCIS / FRGSHPUSM649NCIS"}
    except Exception as e:
        print(f"cass proxy FAILED: {e}", file=sys.stderr)
    for k, s in YAHOO.items():
        try:
            out["prices"][k] = yahoo_weekly(s)
            print(f"Yahoo {s}: {len(out['prices'][k]['close'])} weeks, last {out['prices'][k]['last']}")
        except Exception as e:
            print(f"Yahoo {s} FAILED: {e}", file=sys.stderr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("wrote", OUT, OUT.stat().st_size, "bytes")

if __name__ == "__main__":
    main()
