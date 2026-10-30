"""Advanced interactive workspaces layered onto the validated valuation terminal."""
from dataclasses import replace
from datetime import timedelta
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fixed_income.analytics import price_grid, risk_surface, curve_price, portfolio_values
from fixed_income.bonds import Bond
from fixed_income.charts import mesh_surface, RISK_SCALE

CURRENCIES = 'EUR USD GBP CHF JPY CAD AUD NZD SEK NOK DKK PLN CZK HUF CNY HKD SGD INR BRL MXN ZAR KRW AED SAR'.split()


def plot(fig, title):
    fig.update_layout(template='plotly_white', title=title, paper_bgcolor='#ffffff',
                      plot_bgcolor='#ffffff', font=dict(color='#334155'), height=550, margin=dict(l=20,r=20,t=60,b=30))
    st.plotly_chart(fig, use_container_width=True)


@st.cache_data(show_spinner=False)
def cached_surface(bond, benchmark, spread, x, y):
    return risk_surface(bond, benchmark, spread, x, y)


def surface_panel(bond, model_yield, currency):
    st.subheader('3D / Exact risk surface')
    st.caption('Deterministic fixed-rate bullet cash flows · nominal yield = benchmark + credit spread. This additive spread model is not an option-adjusted or default model.')
    controls = st.sidebar.expander('3D surface controls', expanded=True)
    a = b = c = controls
    benchmark = a.number_input('Initial benchmark yield (%)', value=float(model_yield*100), step=.05)/100
    spread = b.number_input('Initial credit spread (bp)', value=0.0, step=5.0)/10000
    quantity = c.number_input('Position quantity', min_value=.01, value=1.0)
    mode = controls.selectbox('Surface measure', ['Dirty price','Price change (%)','Position profit/loss','Modified duration','Convexity'])
    a = b = c = controls
    xr = a.slider('Benchmark shock range (bp)', -1000,1000,(-200,200),25)
    yr = b.slider('Spread shock range (bp)', -1000,1000,(-100,300),25)
    resolution = c.select_slider('Surface grid resolution', [15,25,41,61,81], value=41)
    if xr[0] == xr[1] or yr[0] == yr[1]:
        st.warning('Choose ranges with distinct endpoints.'); return
    x = np.linspace(*xr,resolution); y = np.linspace(*yr,resolution)
    a = b = controls
    sx = a.slider('Selected benchmark shock (bp)', xr[0],xr[1],max(xr[0],min(0,xr[1])))
    sy = b.slider('Selected spread shock (bp)', yr[0],yr[1],max(yr[0],min(0,yr[1])))
    base = float(price_grid(bond, benchmark+spread))
    prices = cached_surface(bond,benchmark,spread,x,y)
    selected = float(price_grid(bond, benchmark+spread+(sx+sy)/10000))
    if mode in ['Modified duration','Convexity']:
        st.caption('Hypothetical regular bonds: identical face, coupon, settlement and frequency; maturity varies in calendar days. Selected shock marker applies only to shock surfaces.')
        x = np.linspace(max(-.5,benchmark+spread-.03),benchmark+spread+.05,resolution)
        years = controls.slider('Hypothetical maturity range (years)',1,50,(1,30))
        y = np.linspace(*years,resolution)
        key = 'modified' if mode == 'Modified duration' else 'convexity'
        z = np.array([[replace(bond,maturity=bond.settlement+timedelta(days=round(t*365.25))).value(float(v))[key] for v in x] for t in y])
        x=x*100; xlabel='YTM (%)'; ylabel='Years to maturity'; point=None
    else:
        z = prices if mode=='Dirty price' else (prices/base-1)*100 if mode=='Price change (%)' else (prices-base)*quantity
        pz = selected if mode=='Dirty price' else (selected/base-1)*100 if mode=='Price change (%)' else (selected-base)*quantity
        point=(sx,sy,pz); xlabel='Benchmark shock (bp)'; ylabel='Spread shock (bp)'
    fig = mesh_surface(x, y, z, xlabel, ylabel, mode)
    st.caption('Scenario nodes S1–S9 sample the displayed grid. Dotted guides project values onto the floor; highlighted lines show central axis slices, not forecasts over time.')
    if point:
        fig.add_trace(go.Scatter3d(x=[point[0]],y=[point[1]],z=[point[2]],mode='markers',marker=dict(size=7,color='#7c3aed',line=dict(color='#ffffff',width=2)),name='Selected scenario'))
    if controls.button('Reset surface camera'):
        st.session_state['surface_camera_revision'] = st.session_state.get('surface_camera_revision', 0) + 1
    fig.update_layout(uirevision=f"{mode}-{st.session_state.get('surface_camera_revision', 0)}")
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo':False, 'scrollZoom':True}, key='hero_risk_surface')
    a,b,c = st.columns(3)
    a.metric('SELECTED DIRTY PRICE', f'{currency} {selected:,.2f}')
    b.metric('SELECTED CHANGE', f'{(selected/base-1)*100:+.3f}%')
    c.metric('POSITION P/L', f'{currency} {(selected-base)*quantity:+,.2f}')
    st.download_button('Export interactive surface HTML',fig.to_html(include_plotlyjs=True),'bond_risk_surface.html','text/html')
    contours = st.checkbox('Show heatmap contours',value=True)
    heat = go.Figure(go.Heatmap(x=x,y=y,z=z,colorscale=RISK_SCALE,colorbar=dict(title=mode)))
    if contours:
        heat.add_trace(go.Contour(x=x,y=y,z=z,showscale=False,contours=dict(coloring='none',showlabels=True),line=dict(color='#64748b',width=1)))
        if np.min(z)<0<np.max(z) and mode in ['Price change (%)','Position profit/loss']:
            heat.add_trace(go.Contour(x=x,y=y,z=z,showscale=False,contours=dict(start=0,end=0,size=1,coloring='none'),line=dict(color='#7c3aed',width=3)))
    heat.update_layout(xaxis_title=xlabel,yaxis_title=ylabel)
    plot(heat,'Synchronized scenario heatmap')
    xx,yy=np.meshgrid(x,y)
    st.download_button('Export surface data',pd.DataFrame({'X':xx.ravel(),'Y':yy.ravel(),mode:z.ravel()}).to_csv(index=False),'surface.csv','text/csv')


def curve_panel(bond):
    st.subheader('Yield curves / manual observations')
    st.caption('Rates below are illustrative editable inputs, not verified market data. Only continuously compounded SPOT rates are used for discounting. Linear interpolation with flat endpoint extrapolation; no par-to-spot conversion is implied.')
    data = st.data_editor(pd.DataFrame({'Tenor (years)':[1.,2.,3.,5.,7.,10.,15.,20.,30.], 'Spot (%)':[3.]*9,'Shock (bp)':[0.]*9}),num_rows='dynamic',key='spot_curve',hide_index=True)
    data=data.sort_values('Tenor (years)')
    t=data['Tenor (years)'].to_numpy(float); r=data['Spot (%)'].to_numpy(float)/100; shocks=data['Shock (bp)'].to_numpy(float)
    base=curve_price(bond,t,r); shocked=curve_price(bond,t,r,shocks)
    a,b,c=st.columns(3)
    a.metric('SPOT-CURVE DIRTY VALUE',f'{base:,.2f}')
    b.metric('SHOCKED VALUE',f'{shocked:,.2f}')
    c.metric('CURVE SCENARIO CHANGE',f'{shocked-base:+,.2f}')
    fig=go.Figure()
    fig.add_scatter(x=t,y=r*100,name='Base spot')
    fig.add_scatter(x=t,y=r*100+shocks/100,name='Shocked spot')
    plot(fig,'Continuously compounded spot curves (%)')
    forward=np.diff(t*r)/np.diff(t)
    st.dataframe(pd.DataFrame({'Start (years)':t[:-1],'End (years)':t[1:],'Continuous forward (%)':forward*100}),hide_index=True)
    durations=[]
    for i in range(len(t)):
        bump=np.zeros(len(t)); bump[i]=1
        up=curve_price(bond,t,r,bump); down=curve_price(bond,t,r,-bump)
        durations.append((down-up)/(2*base*.0001))
    st.dataframe(pd.DataFrame({'Tenor':t,'Key rate duration (years)':durations}),hide_index=True)
    st.caption('Key rate duration uses symmetric 1 bp bumps to each interpolated spot node, holding contractual cash flows fixed.')


def portfolio_panel(bond, ytm, currency):
    st.subheader('Portfolio / comparison laboratory')
    st.caption('Manual model yields; values are exact dirty DCF prices. Quantity multiplies the entered face. Positive long positions only. FX quotes are reporting-currency units per local unit.')
    default=pd.DataFrame([{'Name':'Selected bond','Currency':currency,'Face':bond.face,'Coupon (%)':bond.coupon*100,'Maturity':bond.maturity.isoformat(),'Yield (%)':ytm*100,'Frequency':bond.frequency,'Quantity':1.,'Spread (bp)':0.}])
    uploaded=st.file_uploader('Load portfolio CSV',type=['csv'])
    if uploaded:
        default=pd.read_csv(uploaded)
        if not set(['Name','Currency','Face','Coupon (%)','Maturity','Yield (%)','Frequency','Quantity','Spread (bp)']).issubset(default.columns):
            st.error('Use the exported portfolio column format.'); return
    rows=st.data_editor(default,num_rows='dynamic',key='positions',hide_index=True)
    if rows.empty: st.info('Add a position to calculate portfolio risk.'); return
    reporting=st.selectbox('Reporting currency',CURRENCIES,index=CURRENCIES.index(currency))
    fx_date=st.date_input('FX valuation date',bond.settlement)
    fx_source=st.text_input('FX source / description',value='Manual user input')
    fx={}
    for cur in sorted(set(rows.Currency)-{reporting}):
        fx[cur]=st.number_input(f'{reporting} per 1 {cur}',min_value=0.,value=0.,format='%.6f')
    values=portfolio_values(rows.to_dict('records'),bond.settlement,reporting,fx)
    table=pd.DataFrame([{k:v for k,v in p.items() if not k.startswith('_')} for p in values])
    total=table.Value.sum(); weights=table.Value/total
    a,b,c,d=st.columns(4)
    a.metric('PORTFOLIO VALUE',f'{reporting} {total:,.2f}')
    b.metric('AGGREGATE DV01',f'{reporting} {table.DV01.sum():,.4f}')
    c.metric('MV-WEIGHTED DURATION',f'{np.dot(weights,table.Duration):.3f} yr')
    d.metric('MV-WEIGHTED YIELD',f'{np.dot(weights,table["Yield (%)"]):.3f}%')
    st.caption('Weighted yield is a descriptive market-value average, not a portfolio IRR. All bond prices and risk use each row’s yield.')
    st.dataframe(table,hide_index=True)
    st.download_button('Save portfolio CSV',rows.to_csv(index=False),'portfolio.csv','text/csv')
    st.download_button('Save FX assumptions',json.dumps({'reporting':reporting,'date':str(fx_date),'source':fx_source,'rates':fx},indent=2),'fx_assumptions.json','application/json')
    fig=go.Figure(go.Pie(labels=table.Name,values=table.Value,hole=.65)); plot(fig,'Market-value composition')
    comparison=go.Figure()
    for p in values[:10]:
        rates=np.linspace(max(-.5,float(p['Yield (%)'])/100-.03),float(p['Yield (%)'])/100+.05,60)
        comparison.add_scatter(x=rates*100,y=price_grid(p['_bond'],rates)/p['Face']*100,name=p['Name'])
    plot(comparison,'Price–yield comparison / dirty quote per 100')
    a,b=st.columns(2)
    shock=a.slider('Portfolio benchmark shock (bp)',-500,500,100)
    spread=b.slider('Portfolio spread shock (bp)',-500,500,0)
    x=np.linspace(-300,300,31); y=np.linspace(-300,300,31); z=np.zeros((31,31)); selected=0.
    for p in values:
        base_y=float(p['Yield (%)'])/100
        # Input yield already includes the row's credit spread; shock it once.
        base=float(price_grid(p['_bond'],base_y))
        scale=float(p['Quantity'])*p['_fx']
        z+=(risk_surface(p['_bond'],base_y,0,x,y)-base)*scale
        selected+=(float(price_grid(p['_bond'],base_y+(shock+spread)/10000))-base)*scale
    st.metric('PORTFOLIO SCENARIO P/L',f'{reporting} {selected:+,.2f}')
    fig=mesh_surface(x,y,z,'Benchmark shock (bp)','Spread shock (bp)',f'P/L ({reporting})')
    fig.update_layout(scene=dict(xaxis_title='Benchmark shock (bp)',yaxis_title='Spread shock (bp)',zaxis_title=f'P/L ({reporting})'))
    plot(fig,'Portfolio / exact risk surface')


def reinvestment_panel(bond,ytm,result,currency):
    st.subheader('Cash flows / reinvestment')
    rate=st.slider('Annual effective reinvestment rate (%)',-20.,25.,3.,.25)/100
    flows=result['flows'].copy()
    horizon=(bond.maturity-bond.settlement).days/365.25
    remaining=np.array([(bond.maturity-d).days/365.25 for d in flows['Payment date']])
    flows['Reinvested coupon at maturity']=flows.Coupon*(1+rate)**remaining
    terminal=flows['Reinvested coupon at maturity'].sum()+flows.Principal.sum()
    annualized=(terminal/result['dirty'])**(1/horizon)-1
    a,b=st.columns(2)
    a.metric('MATURITY WEALTH',f'{currency} {terminal:,.2f}')
    b.metric('ANNUALIZED HOLD-TO-MATURITY RETURN',f'{annualized*100:.3f}%')
    st.caption('Assumes model dirty purchase price, full contractual payment, reinvestment at a constant effective rate, ACT/365.25 holding years, no tax or costs. This realized-return scenario differs from nominal quoted YTM. No interim sale is modeled.')
    flows['Cumulative coupons']=flows.Coupon.cumsum()
    flows['Cumulative cash flows']=flows['Cash flow'].cumsum()
    st.dataframe(flows,hide_index=True)
    st.download_button('Export reinvestment ledger',flows.to_csv(index=False),'reinvestment.csv','text/csv')


def advanced(bond,ytm,currency,result):
    st.divider()
    workspace=st.sidebar.selectbox('Advanced workspace',['3D risk simulator','Spot curves & key rate risk','Portfolio & comparison','Reinvestment','Sovereign relative value'])
    education=st.sidebar.checkbox('Educational mode',value=False)
    if education:
        st.info('1 bp = 0.01 percentage point. Exact DCF reprices every remaining payment. Duration is first-order yield sensitivity; convexity adds curvature. Spread shocks here change discount yields without modeling default or recovery. FX conversion requires explicit rates.')
    try:
        if workspace=='3D risk simulator': surface_panel(bond,ytm,currency)
        elif workspace=='Spot curves & key rate risk': curve_panel(bond)
        elif workspace=='Portfolio & comparison': portfolio_panel(bond,ytm,currency)
        elif workspace=='Reinvestment': reinvestment_panel(bond,ytm,result,currency)
        else: sovereign_panel(bond)
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        st.error(f'Check analytical inputs: {exc}')


def sovereign_panel(bond):
    st.subheader('Sovereigns / relative value')
    st.warning('All initial yields are illustrative placeholders. Enter verified observations for market analysis. No live market feed is connected.')
    countries=['France · OAT','Germany · Bund','United States · Treasury','United Kingdom · Gilt','Italy · BTP','Spain · Bono','Japan · JGB']
    currency_map=['EUR','EUR','USD','GBP','EUR','EUR','JPY']
    data=st.data_editor(pd.DataFrame({'Sovereign':countries,'Currency':currency_map,'Yield (%)':[3.]*7,'Coupon (%)':[3.]*7}),hide_index=True,key='sovereign_inputs')
    term=st.slider('Sovereign comparison maturity (years)',1,30,10)
    germany=float(data.loc[1,'Yield (%)'])
    rows=[]
    for row in data.to_dict('records'):
        b=replace(bond,coupon=float(row['Coupon (%)'])/100,maturity=bond.settlement+timedelta(days=round(term*365.25)))
        v=b.value(float(row['Yield (%)'])/100)
        rows.append(dict(row,**{'Spread to Bund (bp)':(float(row['Yield (%)'])-germany)*100,'Dirty quote per 100':v['dirty']/bond.face*100,'Duration':v['modified'],'Convexity':v['convexity'],'DV01 per 100':v['dv01']/bond.face*100}))
    st.dataframe(pd.DataFrame(rows),hide_index=True)
    st.caption('Cross-currency yield differences include currency effects and are not pure credit spreads. Valuations are local-currency quotes per 100, with shared user-selected schedule assumptions rather than security-specific national conventions.')
    st.markdown('### France–Germany / OAT stress')
    oat_yield=float(data.loc[0,'Yield (%)'])/100
    terms=np.array([2,5,10,20,30]); shocks=np.array([0,25,50,100,150,200,300,500]); z=[]
    for t in terms:
        b=replace(bond,coupon=float(data.loc[0,'Coupon (%)'])/100,maturity=bond.settlement+timedelta(days=round(t*365.25)))
        base=float(price_grid(b,oat_yield))
        z.append((price_grid(b,oat_yield+shocks/10000)/base-1)*100)
    z=np.array(z)
    st.dataframe(pd.DataFrame(z,index=terms,columns=[f'{s:+} bp' for s in shocks]),use_container_width=True)
    fig=go.Figure(go.Heatmap(x=shocks,y=terms,z=z,colorscale='RdYlGn',colorbar=dict(title='Change %')))
    fig.update_layout(xaxis_title='OAT spread widening (bp)',yaxis_title='Hypothetical maturity (years)')
    plot(fig,'France / exact spread stress heatmap')
    fig=mesh_surface(shocks,terms,z,'OAT widening (bp)','Maturity (years)','Price change (%)')
    fig.update_layout(scene=dict(xaxis_title='OAT widening (bp)',yaxis_title='Maturity (years)',zaxis_title='Price change (%)'))
    plot(fig,'OAT spread / maturity surface')
