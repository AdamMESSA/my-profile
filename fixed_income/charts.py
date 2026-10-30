"""Plot styling shared by the terminal's analytics views."""
import plotly.graph_objects as go

MINT = '#48dfb5'
BLUE = '#6da8ff'


def style(fig, title, yaxis):
    fig.update_layout(title=dict(text=title, font=dict(size=17)),
                      template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)',
                      plot_bgcolor='rgba(0,0,0,0)', height=380,
                      margin=dict(l=20, r=20, t=55, b=25),
                      font=dict(color='#aab9ce'), yaxis_title=yaxis,
                      legend=dict(orientation='h', y=1.14),
                      hovermode='x unified')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#202d40', zerolinecolor='#33425b')
    return fig


def cashflow_chart(flows):
    fig = go.Figure()
    fig.add_bar(x=flows['Payment date'], y=flows['Coupon'], name='Coupon', marker_color=MINT)
    fig.add_bar(x=flows['Payment date'], y=flows['Principal'], name='Principal', marker_color=BLUE)
    fig.update_layout(barmode='stack')
    return style(fig, 'Scheduled cash flows', 'Currency amount')


def mesh_surface(x, y, z, xlabel, ylabel, measure):
    """Large rainbow DCF surface with a true wire grid on sampled valuations."""
    import numpy as np
    x, y, z = np.asarray(x), np.asarray(y), np.asarray(z)
    fig = go.Figure(go.Surface(
        x=x, y=y, z=z, colorscale='Jet',
        colorbar=dict(title=dict(text=measure, side='right'), thickness=18, len=.7),
        lighting=dict(ambient=.75, diffuse=.8, specular=.15, roughness=.8),
        hovertemplate=f'{xlabel}: %{{x:.2f}}<br>{ylabel}: %{{y:.2f}}<br>{measure}: %{{z:.5f}}<extra></extra>'))
    # Bound wire density at high surface resolutions for legibility and speed.
    stride = max(1, int(np.ceil(max(z.shape)/41)))
    wx, wy, wz = [], [], []
    for j in sorted(set(range(0,len(y),stride)) | {len(y)-1}):
        wx.extend([*x, None]); wy.extend([*np.repeat(y[j],len(x)), None]); wz.extend([*z[j], None])
    for i in sorted(set(range(0,len(x),stride)) | {len(x)-1}):
        wx.extend([*np.repeat(x[i],len(y)), None]); wy.extend([*y, None]); wz.extend([*z[:,i], None])
    fig.add_trace(go.Scatter3d(x=wx,y=wy,z=wz,mode='lines',line=dict(color='rgba(15,23,42,0.8)',width=2),hoverinfo='skip',showlegend=False))
    axis=dict(showbackground=True,backgroundcolor='#eef0f3',gridcolor='#c2c8d0',
              zerolinecolor='#9ca3af',color='#d6dce5',showspikes=False)
    fig.update_layout(
        template='plotly_dark', paper_bgcolor='#101318', height=820,
        title=dict(text='EXACT RISK / 3D SURFACE',font=dict(size=18,color='#ffad54')),
        margin=dict(l=5,r=15,t=45,b=5),
        scene=dict(xaxis=dict(axis,title=xlabel), yaxis=dict(axis,title=ylabel),
                   zaxis=dict(axis,title=measure),
                   camera=dict(eye=dict(x=1.5,y=1.55,z=1.05)),
                   aspectmode='manual',aspectratio=dict(x=1.3,y=1.3,z=.85)),
        legend=dict(x=0,y=1))
    return fig
