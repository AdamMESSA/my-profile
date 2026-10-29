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
