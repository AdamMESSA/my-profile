from datetime import date
import numpy as np
import pytest
from fixed_income.bonds import Bond
from fixed_income.analytics import price_grid, risk_surface, curve_price, portfolio_values

@pytest.fixture
def bond():
    return Bond(1000,.04,date(2036,8,31),date(2026,10,30))


def test_vectorized_exact_engine_agreement(bond):
    rates=np.array([[-.03,0,.03],[.04,.07,.10]])
    actual=price_grid(bond,rates)
    for index in np.ndindex(rates.shape):
        assert actual[index]==pytest.approx(bond.value(float(rates[index]))['dirty'])


def test_surface_additive_shocks_and_monotonicity(bond):
    x=np.array([-100,0,100]); y=np.array([-50,0,50])
    grid=risk_surface(bond,.03,.01,x,y)
    assert grid[1,1]==pytest.approx(bond.value(.04)['dirty'])
    assert grid[2,0]==pytest.approx(bond.value(.035)['dirty'])
    assert np.all(np.diff(grid,axis=0)<0)
    assert np.all(np.diff(grid,axis=1)<0)


def test_spot_curve_against_direct_cashflows(bond):
    flows=bond.cashflows()
    expected=np.dot(flows['Cash flow'],np.exp(-.04*flows['Time (years)']))
    assert curve_price(bond,[1,30],[.04,.04])==pytest.approx(expected)
    assert curve_price(bond,[1,30],[.04,.04],[100,100]) < expected


@pytest.mark.parametrize('rates', [[float('nan')],[-2.]])
def test_reject_invalid_yields(bond,rates):
    with pytest.raises(ValueError): price_grid(bond,rates)


def test_reject_invalid_curve(bond):
    with pytest.raises(ValueError): curve_price(bond,[2,1],[.03,.04])


def test_portfolio_requires_fx_and_aggregates(bond):
    row={'Currency':'USD','Face':1000,'Coupon (%)':4,'Maturity':bond.maturity,'Frequency':2,'Yield (%)':4,'Quantity':2}
    with pytest.raises(ValueError): portfolio_values([row],bond.settlement,'EUR',{})
    p=portfolio_values([row],bond.settlement,'EUR',{'USD':.9})[0]
    value=bond.value(.04)
    assert p['Value']==pytest.approx(value['dirty']*1.8)
    assert p['DV01']==pytest.approx(value['dv01']*1.8)
