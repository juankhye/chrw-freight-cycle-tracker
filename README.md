# CHRW Freight Cycle Tracker

Companion to the [C.H. Robinson research dashboard](https://juankhye.github.io/chrw-dashboard/).
One page that scores where the US truckload cycle sits, using every public series that drives
Robinson's gross profit per load, and turns each into a phase vote (A bottom, B squeeze, C catch-up, D top, E bust).

## Data

| File | Contents | Refresh |
|---|---|---|
| `data/auto.json` | Cass shipments & expenditures, truckload PPI, truck-transport employment, diesel (all FRED); weekly prices for CHRW, KNX, SPY (Yahoo) | Daily via GitHub Actions (`.github/workflows/update-data.yml`, runs `scripts/fetch_data.py`) |
| `data/manual.json` | DAT spot/contract, tender rejections, Class 8 orders, FMCSA authority changes, enforcement events, CHRW quarterly KPIs, AGP/day cadence, GS-model price/cost history, signpost statuses, valuation bands, calendar, sources | Edit by hand after each release |

## Updating manual data

1. **Monthly (mid-month):** DAT release → append month to `dat.months`, `dat.van_spot` / `dat.van_contract` (linehaul, ex-fuel) and `van_*_allin`; OTRI to `otri.values`; Class 8 prelim orders to `capacity.class8_orders`; FTR net authority change to `capacity.net_authority`.
2. **Quarterly (after CHRW results):** add a quarter to every array in `chrw_q`; add three months to `agp_day`; update `signposts[].latest/status`; update `valuation.fwd_eps`.
3. **As needed:** `events`, `capacity.enforcement_events`, `phase.note`, `valuation.targets`.

Arrays must stay aligned with their `months` / `quarters` labels. Use `null` for missing values.

Run `python scripts/fetch_data.py` locally to refresh `auto.json` at any time.
