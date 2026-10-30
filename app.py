"""Fixed Income / professional bond valuation terminal."""
from datetime import date, timedelta
from zoneinfo import ZoneInfo
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fixed_income.bonds import Bond, CONVENTIONS
from fixed_income.charts import style, cashflow_chart, MINT, BLUE

st.set_page_config(page_title='FI / Bond Terminal', page_icon='◈', layout='wide')
st.markdown('''<style>
.stApp {background:#101318;color:#e5e7eb} [data-testid="stSidebar"] {background:#181c23} .block-container {padding-top:2rem; max-width:1800px} button[kind="primary"] {background:#f39132}
[data-testid="stSidebar"] {border-right:1px solid #253149}
h1 {font-size:2.35rem!important; letter-spacing:-1.3px}
h3 {font-size:1.15rem!important}
[data-testid="stMetric"] {background:#111b2a;border:1px solid #26334a;border-radius:8px;padding:18px}
[data-testid="stMetricLabel"] {color:#9aacc4;font-size:12px;letter-spacing:.6px}
[data-testid="stMetricValue"] {font-family:monospace;font-size:1.65rem}
.eyebrow {color:#48dfb5;font:12px monospace;letter-spacing:2px;margin-bottom:12px}
.banner {border-top:1px solid #26334a;border-bottom:1px solid #26334a;padding:12px 0;color:#aab9ce;font:12px monospace;margin:20px 0}
</style>''', unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## ◈ FIXED INCOME')
    st.caption('ANALYTICS TERMINAL / 02')
    st.divider()
    st.markdown('### Instrument parameters')
    currency = st.selectbox('Currency', 'EUR USD GBP CHF JPY CAD AUD NZD SEK NOK DKK PLN CZK HUF CNY HKD SGD INR BRL MXN ZAR KRW AED SAR'.split())
    face = st.number_input('Face value', min_value=1.0, max_value=1e12, value=1000.0, step=100.0)
    coupon = st.number_input('Annual coupon rate (%)', 0.0, 100.0, 4.0, .125)
    ytm = st.number_input('Annualized YTM (%)', -50.0, 100.0, 3.5, .05)
    frequency = st.selectbox('Coupon frequency', [2, 1, 4], format_func=lambda f: {1:'Annual', 2:'Semiannual',4:'Quarterly'}[f])
    today = datetime.now(ZoneInfo('Europe/Paris')).date()
    settlement = st.date_input('Settlement date', today, min_value=date(1900,1,1), max_value=date(2200,1,1))
    mode = st.radio('Maturity input', ['Date', 'Years remaining'], horizontal=True)
    if mode == 'Date':
        maturity = st.date_input('Maturity date', settlement.replace(year=settlement.year+10) if not (settlement.month == 2 and settlement.day == 29) else settlement + timedelta(days=3652), min_value=date(1900,1,1), max_value=date(2300,1,1))
    else:
        years = st.number_input('Years to maturity (365.25 days/year)', .01, 99.0, 10.0, .25)
        maturity = settlement + timedelta(days=round(years*365.25))
        st.caption(f'Derived maturity: {maturity:%d %b %Y}')
    convention = st.selectbox('Day-count convention', CONVENTIONS)
    st.divider()
    st.markdown('### Market quote')
    purchase = st.number_input('Bond purchase / market price', min_value=.01, max_value=1e14, value=1020.0, step=1.0, help='Total currency amount for the entire face value, not a quote per 100.')
    price_type = st.radio('Market price basis', ['Clean', 'Dirty'], horizontal=True)
    st.caption('Manual inputs • no live market feed')

st.markdown('<div class="eyebrow">FI / ANALYTICS WORKSPACE</div>', unsafe_allow_html=True)
header, badge = st.columns([4,1])
with header:
    st.title('Fixed income analytics terminal')
    st.caption('Dated cash flows. Transparent pricing. Measurable rate risk.')
with badge:
    st.markdown('**◈ FIXED-RATE BULLET**')
    st.caption('Single instrument · Scenario analytics')
try:
    bond = Bond(face, coupon/100, maturity, settlement, frequency, convention)
    result = bond.value(ytm/100)
    implied = bond.yield_from_price(purchase, price_type)
    market_dirty = purchase + bond.accrued if price_type == 'Clean' else purchase
    market_clean = market_dirty - bond.accrued
    if market_clean <= 0:
        raise ValueError('The market quote implies a nonpositive clean price; increase the quote.')
except (ValueError, OverflowError) as exc:
    st.error(str(exc))
    st.stop()

money = lambda x: f'{currency} {x:,.2f}'
st.markdown(f'<div class="banner">{currency} &nbsp; / &nbsp; {coupon:.3f}% COUPON &nbsp; / &nbsp; MATURITY {maturity:%d %b %Y} &nbsp; / &nbsp; {frequency} PAYMENTS PER YEAR &nbsp; / &nbsp; {convention}</div>', unsafe_allow_html=True)
metrics = {
    'Clean price': (money(result['clean']), 'Dirty price minus accrued interest; currency amount.'),
    'Dirty price': (money(result['dirty']), 'Sum of discounted future contractual cash flows; currency amount.'),
    'Market YTM': (f'{implied*100:.4f}%', 'Nominal annual yield solving model dirty price = market dirty price.'),
    'DV01': (f'{currency} {result["dv01"]:,.4f}', 'Dirty price × modified duration × 0.0001; positive magnitude of first-order value change per bp.'),
    'Modified duration': (f'{result["modified"]:.4f} yr', 'Macaulay duration / (1 + yield/frequency); first-order proportional sensitivity.'),
    'Convexity': (f'{result["convexity"]:.4f} yr²', 'Second yield derivative divided by dirty price; curvature of the price–yield relationship.'),
    'Accrued interest': (money(result['accrued']), 'Face × annual coupon × elapsed day-count fraction since the prior coupon.'),
    'Remaining coupon income': (money(result['flows']['Coupon'].sum()), 'Undiscounted sum of remaining coupons; excludes reinvestment.'),
    'Redemption value': (money(face), 'Principal repaid at maturity under the bullet bond contract.'),
    'Remaining maturity': (f'{(maturity-settlement).days/365.25:.3f} yr', 'Calendar days to maturity divided by 365.25; informational, not discount time.')}
selected_metrics = st.sidebar.multiselect('Dashboard metrics', list(metrics), default=['Clean price','Dirty price','Market YTM','DV01'])
for offset in range(0,len(selected_metrics),4):
    for col,name in zip(st.columns(4),selected_metrics[offset:offset+4]):
        value,help_text=metrics[name]
        col.metric(name,value,help=help_text)
st.caption(f'Model yield: {ytm:.3f}% nominal annual, compounded {frequency}× yearly. Prices are total currency amounts; model clean quote per 100 face: {result["clean"]/face*100:.4f}.')

valuation, risk, ledger, methodology = st.tabs(['VALUATION', 'RATE RISK', 'CASH-FLOW LEDGER', 'METHODOLOGY'])
with valuation:
    left, right = st.columns([1.6,1])
    with left:
        st.plotly_chart(cashflow_chart(result['flows']), use_container_width=True)
    with right:
        st.markdown('### Valuation breakdown')
        breakdown = pd.DataFrame({'Component':['PV of coupons','PV of principal','Dirty / full price','Accrued interest','Clean price','Market clean price','Model − market clean','Remaining nominal cash flows'],
            f'Amount ({currency})':[result['pv_coupons'],result['pv_principal'],result['dirty'],result['accrued'],result['clean'],market_clean,result['clean']-market_clean,result['nominal']]})
        st.dataframe(breakdown, hide_index=True, use_container_width=True, column_config={f'Amount ({currency})':st.column_config.NumberColumn(format='%.4f')})
    a,b,c = st.columns(3)
    a.metric('CURRENT YIELD · MARKET CLEAN', f'{face*coupon/100/market_clean*100:.3f}%')
    b.metric('NEXT COUPON', f'{bond.schedule()[1]:%d %b %Y}')
    c.metric('REMAINING PAYMENTS', len(result['flows']))
    st.caption('Current yield = annual coupon / market clean price. Nominal cash flows exclude payments on or before settlement; they are not a return forecast.')
with risk:
    a,b,c,d = st.columns(4)
    a.metric('MACAULAY DURATION', f'{result["macaulay"]:.4f} yr')
    b.metric('MODIFIED DURATION', f'{result["modified"]:.4f} yr')
    c.metric('DOLLAR DURATION', f'{currency} {result["dollar_duration"]:,.2f}')
    d.metric('CONVEXITY', f'{result["convexity"]:.4f} yr²')
    st.caption('Risk is measured at the input model YTM using dirty price. Dollar duration is currency sensitivity per 1.00 yield change; DV01/PVBP is its positive magnitude per 1 basis point.')
    shock = st.slider('Parallel yield shock (basis points)', -500, 500, 100, 5)
    dy = shock/10000
    exact = bond.value(ytm/100+dy)['dirty']
    approximate = result['dirty'] * (1-result['modified']*dy+.5*result['convexity']*dy**2)
    x,y,z = st.columns(3)
    x.metric('SHOCKED DIRTY PRICE', money(exact), f'{exact-result["dirty"]:+.2f}', delta_color='off')
    y.metric('DURATION + CONVEXITY ESTIMATE', money(approximate))
    z.metric('APPROXIMATION ERROR', money(approximate-exact))
    shifts = np.linspace(-500,500,101)
    yields = ytm/100+shifts/10000
    prices = [bond.value(float(rate))['dirty'] for rate in yields]
    fig = go.Figure()
    fig.add_scatter(x=yields*100, y=prices, name='Exact repricing', line=dict(color=MINT,width=3))
    fig.add_scatter(x=yields*100, y=result['dirty']*(1-result['modified']*shifts/10000+.5*result['convexity']*(shifts/10000)**2), name='Duration + convexity', line=dict(color=BLUE,dash='dot'))
    fig.add_scatter(x=[ytm], y=[result['dirty']], name='Model yield', mode='markers', marker=dict(color='#ffbc69',size=11))
    fig.update_xaxes(title='Nominal annual YTM (%)')
    st.plotly_chart(style(fig,'Price–yield sensitivity',f'Dirty price ({currency})'),use_container_width=True)
    shocks = np.array([-200,-100,-50,-1,0,1,50,100,200])
    scenario_prices = np.array([bond.value(ytm/100+float(s)/10000)['dirty'] for s in shocks])
    st.dataframe(pd.DataFrame({'Shock (bp)':shocks,'YTM (%)':ytm+shocks/100,'Dirty price':scenario_prices,'Price change':scenario_prices-result['dirty'],'Change (%)':(scenario_prices/result['dirty']-1)*100}),hide_index=True,use_container_width=True)
with ledger:
    st.markdown('### Discounted payment schedule')
    st.caption(f'Settlement {settlement:%d %b %Y} · Currency {currency} · Discounted at model YTM {ytm:.3f}%')
    st.dataframe(result['flows'], hide_index=True, use_container_width=True,
                 column_config={col:st.column_config.NumberColumn(format='%.6f') for col in result['flows'].columns if col != 'Payment date'})
    st.download_button('↓ Export cash-flow ledger', result['flows'].to_csv(index=False).encode(), 'bond_cashflows.csv', 'text/csv')
    summary = {k:v for k,v in result.items() if k != 'flows'}
    summary.update(currency=currency, model_ytm=ytm/100, market_ytm=implied, market_price=purchase, market_price_basis=price_type)
    st.download_button('↓ Export valuation summary',pd.DataFrame([summary]).to_csv(index=False).encode(),'bond_valuation.csv','text/csv')
with methodology:
    st.markdown('''### Pricing conventions
This terminal values **regular fixed-rate, noncallable bullet bonds**. A full regular coupon schedule is inferred backward from maturity, preserving end-of-month dates. Coupon cash amounts equal face × annual coupon / frequency. There is no issue-date input or stub-period handling.

Settlement on a payment date excludes that payment and resets accrued interest to zero. Dates are unadjusted: no holiday calendar, business-day lag, ex-coupon period, default risk, tax, or embedded option model is applied. Currency is a display unit; no FX conversion occurs.

**Annualized YTM** is a nominal rate compounded at the coupon frequency, not an effective annual yield. All displayed prices are currency amounts for the entire face value. Purchase price is interpreted using the selected clean/dirty basis; model valuation and model risk use the input YTM, while implied YTM uses the market quote.
''')
    st.latex(r'P_{dirty}=\sum_i CF_i(1+y/f)^{-ft_i},\qquad P_{clean}=P_{dirty}-AI')
    st.latex(r'D_M=\frac{\sum_i t_i PV_i}{P},\quad D_{mod}=\frac{D_M}{1+y/f},\quad DV01=P D_{mod}\times10^{-4}')
    st.latex(r'C=\frac{\sum_i t_i(t_i+1/f)PV_i}{P(1+y/f)^2}')
    st.markdown('''**Day counts:** ACT/ACT ICMA counts actual days relative to each regular reference coupon period; each whole period is 1/f years. ACT/365F and ACT/360 use actual days over fixed denominators. 30E/360 caps each day-of-month at 30. The chosen convention controls accrued interest and discount times; coupons remain fixed. Other market-specific yield conventions may differ.

**Numerics:** implied yield is solved with a bracketed Brent method in log-compounding-factor space. Duration and convexity are analytic derivatives of the stated pricing model. Scenario analysis reprices the same contractual cash flows with a parallel YTM change. Nominal cash flows assume full contractual payment and exclude reinvestment.
''')
    st.info('Analytical valuation from manual inputs. No live quotes or credit/option adjustments are included.')
st.divider()
st.caption('FI / BOND TERMINAL     •     DATED CASH-FLOW ENGINE     •     MANUAL MARKET INPUTS')

from fixed_income.workspaces import advanced
advanced(bond, ytm/100, currency, result)
