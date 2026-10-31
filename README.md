# FI / Bond Valuation Terminal

An interactive Streamlit workspace for regular fixed-rate bullet bonds. Uses Python, NumPy, Pandas, SciPy, and Plotly. The original profile-site files are preserved.

## Run

```bash
cd /workspace/my-profile
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
.venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Open the Streamlit service using your hosting platform's supported access route. GitHub Pages cannot execute this Python application; use a Python/Streamlit host for deployment.

## Validate

```bash
.venv/bin/python -m pytest -q
```

Tests cover par pricing, a reference duration, zero coupons, analytic risk versus finite differences, negative-yield price inversion, day counts, leap-year/end-of-month schedules, invalid inputs, and Streamlit interaction smoke checks.

## Features

- Date or remaining-year maturity input, settlement, frequency, currency, and four day counts.
- Model clean/dirty prices, accrued interest, coupon/principal present values, market-implied YTM, current yield, duration, dollar duration, DV01/PVBP, convexity, and remaining nominal cash flows.
- Cash-flow chart, exact price–yield curve, duration/convexity approximation, selectable rate shock, scenario grid, and CSV exports.
- Modular financial engine in `fixed_income/bonds.py`, chart helpers in `fixed_income/charts.py`, and interface in `app.py`.

## Financial conventions and scope

All monetary inputs are total amounts for the entered face, not quotes per 100. The UI separately displays the model clean quote per 100. YTM is nominal annual compounded at the coupon frequency. Purchase price can be clean or dirty. Risk metrics use the model yield and dirty price; current yield uses the market clean price.

The schedule is inferred backward from maturity using regular fixed coupon amounts, with end-of-month preservation. Settlement-date coupons are excluded. There is no issue date, stub schedule, holiday adjustment, ex-coupon handling, callable feature, default model, tax, FX conversion, or live market feed. Remaining maturity is limited to 100 years.

ACT/ACT ICMA uses reference coupon periods; ACT/365F and ACT/360 use actual days with fixed denominators; 30E/360 caps each date's day at 30. The selected convention controls both accrual and discount times. This explicit model may differ from security-specific market quoting conventions. Macaulay duration uses these discount times; modified duration and convexity are analytic derivatives of this model.

`P = Σ CF × (1 + y/f)^(-f×t)`. Dirty = clean + accrued. Dollar duration is positive `P × modified duration` per unit yield; DV01 is that magnitude × 0.0001. Convexity uses `Σ[t(t+1/f)PV] / [P(1+y/f)^2]`. YTM inversion uses Brent's method in log-compounding-factor space. Contractual cash flows assume full payment and do not include reinvestment income.

## Terminal 2.0 analytical workspaces

Use the dedicated **Workspace** navigation in the sidebar. Only the selected
workspace is rendered; valuation, rate risk, the cash-flow ledger and methodology
share the **Valuation & cash flows** destination. The validated `Bond` engine and
its original tests are retained. New capabilities include:

- Exact vectorized benchmark/spread risk surfaces, synchronized heatmaps, a
  selected-scenario marker, adjustable ranges/resolution, contours, CSV data and
  interactive HTML export. Duration/convexity surfaces use hypothetical bonds
  with regenerated valid maturity-anchored schedules.
- Editable continuously compounded spot curves, node-specific shocks, forward
  rates, and symmetric-bump key rate durations. Par-rate bootstrapping is not implied.
- Editable long-only portfolios, CSV import/export, explicit dated/source-labeled
  manual FX inputs, market-value weights, additive DV01, comparison curves and
  exact aggregated risk surfaces. Input yields already include credit spreads.
- Hypothetical global sovereign comparison and France spread/maturity stress.
- Reinvestment-rate scenarios, maturity wealth and effective annual holding returns.
- 24 currency labels, configurable headline metrics and educational explanations.

The model remains **regular fixed-rate bullet bonds**, including a zero coupon
by setting coupon to zero. Expanded contractual coupon structures, stub periods,
holiday adjustment, arbitrary frequencies, Excel import/export, portfolio short
positions and live data are not implemented. Sovereign examples use shared model
conventions, not country-specific security conventions. Imported portfolios must
use the exported CSV column schema. CSV holdings exports do not include FX assumptions. Use the JSON workspace
export below to restore holdings together with explicit FX rates and provenance. Cross-currency yield spreads are not pure
credit spreads. Model YTM discounting and continuous-spot-curve discounting are
separate analyses and need not produce the same valuation.

## Navigation, portfolios, scenarios, and saved workspaces

- **Portfolio overview** shows reporting-currency value, aggregate DV01, weighted
  duration/yield, market-value composition and position risk contributions. Position
  weights and DV01 shares each sum to 100%; duration and convexity contributions
  sum to the portfolio's market-value-weighted measures. Risk amounts include
  quantity and explicit FX conversion. Export the contribution table as CSV.
- **Portfolio & comparison** uses the same holdings and adds comparison curves and
  an exact portfolio shock surface. Edits persist when navigating between views.
- **Named scenarios** lets you add, rename, and remove benchmark/spread shocks.
  Names must be unique and nonempty. Select the current bond or saved portfolio;
  each scenario reprices contractual cash flows exactly. Portfolio scenarios use
  each holding's yield, quantity, and saved FX rate, holding FX constant. Input
  yields already include credit spreads, so only scenario spread changes are added.
- **Save workspace JSON** downloads a versioned snapshot containing instrument
  inputs, visited workspace controls, metric selections, holdings, FX rates/date/
  source, spot curves, sovereign observations and named scenarios. Restore it with
  **Workspace save / restore → Restore workspace JSON**. Downloads capture the
  current edits. Workspace files contain manual financial inputs; they do not
  contain credentials, live market data, generated charts or valuation results.

Restoring replaces the current saved inputs and tables after validating the JSON
format, version and input types. Invalid files leave the workspace untouched.
Controls outside their supported options/ranges revert to defaults with a warning;
invalid analytical tables display input errors for correction. Files are limited
to 2 MB and 1,000 rows per table. Unvisited views use their normal defaults.
Browser refreshes/new sessions require a saved JSON file; no server-side workspace
account or automatic disk storage is implied. CSV holdings import remains available
and replaces the portfolio only when a new file is loaded.

Tests additionally cover all navigation destinations, contribution reconciliation,
exact single-bond and portfolio scenarios, invalid workspace rejection, atomic
restore, restored FX and curves, and table retention across page changes.
