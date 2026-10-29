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
