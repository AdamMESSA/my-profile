"""Plot styling shared by the terminal's analytics views."""
import plotly.graph_objects as go

MINT = '#fc734d'
BLUE = '#0097de'
RISK_SCALE = [[0, '#102f46'], [.25, '#007cb8'], [.5, '#0097de'], [.75, '#e3ae87'], [1, '#fc734d']]


def style(fig, title, yaxis):
    fig.update_layout(title=dict(text=title, font=dict(size=17)),
                      template='plotly_dark', colorway=[BLUE,MINT,'#ffb08c','#65c9ec'], paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)', height=380,
                      margin=dict(l=20, r=20, t=55, b=25),
                      font=dict(color='#b1bad0'), yaxis_title=yaxis,
                      legend=dict(orientation='h', y=1.14),
                      hovermode='x unified')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#294555', zerolinecolor='#4a697b')
    return fig


def cashflow_chart(flows):
    fig = go.Figure()
    fig.add_bar(x=flows['Payment date'], y=flows['Coupon'], name='Coupon', marker_color=MINT)
    fig.add_bar(x=flows['Payment date'], y=flows['Principal'], name='Principal', marker_color=BLUE)
    fig.update_layout(barmode='stack')
    return style(fig, 'Scheduled cash flows', 'Currency amount')


def mesh_surface(x, y, z, xlabel, ylabel, measure):
    """Black analytical scene with valuation mesh, scenario nodes and projections."""
    import numpy as np
    x, y, z = np.asarray(x), np.asarray(y), np.asarray(z)
    fig = go.Figure(go.Surface(
        x=x, y=y, z=z, colorscale=RISK_SCALE, opacity=.82,
        colorbar=dict(title=dict(text=measure, side='right'), thickness=18, len=.7),
        lighting=dict(ambient=.85, diffuse=.55, specular=.12, roughness=.9),
        hovertemplate=f'{xlabel}: %{{x:.2f}}<br>{ylabel}: %{{y:.2f}}<br>{measure}: %{{z:.5f}}<extra></extra>'))
    # Bound wire density at high surface resolutions for legibility and speed.
    stride = max(1, int(np.ceil(max(z.shape)/21)))
    wx, wy, wz = [], [], []
    for j in sorted(set(range(0,len(y),stride)) | {len(y)-1}):
        wx.extend([*x, None]); wy.extend([*np.repeat(y[j],len(x)), None]); wz.extend([*z[j], None])
    for i in sorted(set(range(0,len(x),stride)) | {len(x)-1}):
        wx.extend([*np.repeat(x[i],len(y)), None]); wy.extend([*y, None]); wz.extend([*z[:,i], None])
    fig.add_trace(go.Scatter3d(x=wx,y=wy,z=wz,mode='lines',line=dict(color='rgba(110,159,210,0.28)',width=1),hoverinfo='skip',showlegend=False))
    # Nine sampled scenarios and their floor projections expose the dimensions
    # without inventing market observations or an implied path through time.
    rows = sorted({0, len(y)//2, len(y)-1})
    cols = sorted({0, len(x)//2, len(x)-1})
    nodes = [(x[i], y[j], z[j,i]) for j in rows for i in cols]
    floor = float(np.min(z)) - max(float(np.ptp(z))*.1, .01)
    px, py, pz = [], [], []
    for nx, ny, nz in nodes:
        px.extend([nx,nx,None]); py.extend([ny,ny,None]); pz.extend([floor,nz,None])
    fig.add_trace(go.Scatter3d(x=px,y=py,z=pz,mode='lines',
        line=dict(color='rgba(165,193,205,0.5)',width=2,dash='dot'),
        hoverinfo='skip',showlegend=False))
    fig.add_trace(go.Scatter3d(x=[p[0] for p in nodes],y=[p[1] for p in nodes],z=[p[2] for p in nodes],
        mode='markers+text',text=[f'S{i+1}' for i in range(len(nodes))],textposition='top center',
        textfont=dict(size=11,color='#c8d2e9'),
        marker=dict(size=5,color=[p[2] for p in nodes],colorscale=RISK_SCALE,
                    cmin=float(z.min()),cmax=float(z.max()),line=dict(color='#02070a',width=1)),
        name='Sampled scenarios',
        hovertemplate=f'%{{text}}<br>{xlabel}: %{{x:.2f}}<br>{ylabel}: %{{y:.2f}}<br>{measure}: %{{z:.5f}}<extra></extra>'))
    # Highlight two orthogonal slices of the same calculated surface.
    for i, (cx, cy, cz) in enumerate([
        (x, np.repeat(y[len(y)//2],len(x)), z[len(y)//2]),
        (np.repeat(x[len(x)//2],len(y)), y, z[:,len(x)//2])]):
        fig.add_trace(go.Scatter3d(x=cx,y=cy,z=cz,mode='lines',
            line=dict(color=['#0097de','#fc734d'][i],width=4),
            name=['Benchmark slice','Spread slice'][i] if 'shock' in xlabel.lower() else ['X-axis slice','Y-axis slice'][i],
            hoverinfo='skip'))
    axis=dict(showbackground=True,backgroundcolor='rgba(10,30,43,0.55)',gridcolor='#294555',
              zerolinecolor='#4a697b',color='#c8d2e9',showspikes=False,
              showline=True,linecolor='#4a697b',tickfont=dict(size=11))
    fig.update_layout(
        template='plotly_dark', colorway=[BLUE,MINT,'#ffb08c','#65c9ec'], paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#c8d2e9'), height=820,
        title=dict(text='SCENARIO SPACE / EXACT VALUATION',font=dict(size=17,color='#edf2f7')),
        margin=dict(l=5,r=15,t=45,b=5),
        scene=dict(bgcolor='rgba(0,0,0,0)',xaxis=dict(axis,title=xlabel), yaxis=dict(axis,title=ylabel),
                   zaxis=dict(axis,title=measure,range=[floor,float(z.max())+max(float(np.ptp(z))*.08,.01)]),
                   camera=dict(eye=dict(x=1.65,y=1.65,z=1.15),projection=dict(type='orthographic')),
                   aspectmode='manual',aspectratio=dict(x=1.3,y=1.3,z=.85)),
        legend=dict(x=0,y=1,orientation='h',font=dict(size=11,color='#b1bad0'),bgcolor='rgba(0,0,0,0)'))
    return fig
