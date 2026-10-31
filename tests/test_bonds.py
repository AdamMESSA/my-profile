from datetime import date
import pytest
from fixed_income.bonds import Bond, shift_months, year_fraction, CONVENTIONS


def test_par_and_textbook_duration():
    b = Bond(1000, .05, date(2030,1,1), date(2025,1,1), 2)
    v = b.value(.05)
    assert v['dirty'] == pytest.approx(1000)
    assert v['accrued'] == 0
    assert v['nominal'] == 1250
    assert v['macaulay'] == pytest.approx(4.4854327646)
    assert v['pv_coupons'] + v['pv_principal'] == pytest.approx(v['dirty'])


@pytest.mark.parametrize('convention', CONVENTIONS)
@pytest.mark.parametrize('frequency', [1,2,4])
@pytest.mark.parametrize('rate', [-.02,0,.07])
def test_implied_yield_roundtrip(convention,frequency,rate):
    b = Bond(1000,.04,date(2032,8,31),date(2026,10,29),frequency,convention)
    v = b.value(rate)
    assert b.yield_from_price(v['clean']) == pytest.approx(rate, abs=1e-11)
    assert b.yield_from_price(v['dirty'],'Dirty') == pytest.approx(rate, abs=1e-11)
    assert v['dirty']-v['clean'] == pytest.approx(v['accrued'])


def test_derivatives():
    b = Bond(1000,.04,date(2036,4,30),date(2026,10,29))
    v = b.value(.035)
    h = 1e-5
    up, down = b.value(.035+h)['dirty'], b.value(.035-h)['dirty']
    assert -(up-down)/(2*h) == pytest.approx(v['dollar_duration'],rel=1e-7)
    assert (up-2*v['dirty']+down)/h**2/v['dirty'] == pytest.approx(v['convexity'],rel=1e-6)
    assert v['dv01'] == pytest.approx(v['dollar_duration']*1e-4)


def test_zero_coupon():
    b = Bond(1000,0,date(2030,1,1),date(2025,1,1),1)
    v = b.value(.05)
    assert v['dirty'] == pytest.approx(1000/1.05**5)
    assert v['macaulay'] == 5
    assert v['accrued'] == 0


def test_coupon_date_and_eom():
    b = Bond(1000,.06,date(2028,8,31),date(2028,2,29),2)
    assert b.schedule() == [date(2028,2,29),date(2028,8,31)]
    assert b.accrued == 0
    assert len(b.cashflows()) == 1
    assert shift_months(date(2028,8,31),-12) == date(2027,8,31)


def test_accrual_and_daycounts():
    b = Bond(1000,.06,date(2027,1,1),date(2026,4,1),2)
    assert b.accrued == pytest.approx(30*90/181)
    assert year_fraction(date(2026,1,31),date(2026,7,31),'30E/360') == .5


@pytest.mark.parametrize('kwargs', [{'face':0},{'coupon':-.1},{'frequency':3},{'settlement':date(2030,1,1)}])
def test_invalid_bond(kwargs):
    params = dict(face=1000,coupon=.04,maturity=date(2030,1,1),settlement=date(2026,1,1))
    params.update(kwargs)
    with pytest.raises(ValueError):
        Bond(**params)


def test_invalid_yield_and_price():
    b = Bond(1000,.04,date(2030,1,1),date(2026,1,1))
    with pytest.raises(ValueError):
        b.value(-2)
    with pytest.raises(ValueError):
        b.yield_from_price(0)
