"""Exact scenario analytics using the existing contractual cash-flow model."""
from dataclasses import replace
import numpy as np
import pandas as pd
from fixed_income.bonds import Bond


def price_grid(bond, yields):
    """Vectorized nominal-yield DCF; preserves the engine's times and frequency."""
    yields = np.asarray(yields, dtype=float)
    if not np.all(np.isfinite(yields)) or np.any(yields <= -bond.frequency):
        raise ValueError('All scenario yields must exceed minus coupon frequency.')
    flows = bond.cashflows()
    factors = np.exp(-bond.frequency * flows['Time (years)'].to_numpy() *
                     np.log1p(yields[..., None] / bond.frequency))
    prices = factors @ flows['Cash flow'].to_numpy()
    if not np.all(np.isfinite(prices)):
        raise ValueError('Scenario prices exceed numerical range.')
    return prices


def risk_surface(bond, benchmark, spread, rate_bp, spread_bp):
    x, y = np.meshgrid(rate_bp, spread_bp)
    return price_grid(bond, benchmark + spread + (x+y)/10000)


def curve_price(bond, tenors, spots, shocks_bp=None):
    """Interpolate continuously compounded spot rates; flat endpoint extrapolation."""
    tenors, spots = np.asarray(tenors, float), np.asarray(spots, float)
    if len(tenors) < 2 or tenors.shape != spots.shape or not np.all(np.isfinite([tenors, spots])) or np.any(tenors <= 0) or np.any(np.diff(tenors) <= 0):
        raise ValueError('Provide finite spot rates at at least two increasing positive tenors.')
    if shocks_bp is not None:
        shocks = np.asarray(shocks_bp, float)
        if shocks.shape != spots.shape or not np.all(np.isfinite(shocks)):
            raise ValueError('Provide one finite shock per tenor.')
        spots = spots + shocks / 10000
    flows = bond.cashflows()
    t = flows['Time (years)'].to_numpy()
    return float(np.dot(flows['Cash flow'], np.exp(-np.interp(t, tenors, spots)*t)))


def portfolio_values(rows, settlement, reporting, fx):
    """Amounts are per bond face times quantity; FX is reporting units per local unit."""
    output = []
    for row in rows:
        currency = str(row['Currency'])
        rate = 1.0 if currency == reporting else float(fx.get(currency, float('nan')))
        quantity = float(row['Quantity'])
        if not np.isfinite(rate) or rate <= 0:
            raise ValueError(f'Positive FX rate required for {currency} into {reporting}.')
        if not np.isfinite(quantity) or quantity <= 0:
            raise ValueError('Position quantities must be positive and finite.')
        bond = Bond(float(row['Face']), float(row['Coupon (%)'])/100,
                    pd.Timestamp(row['Maturity']).date(), settlement, int(row['Frequency']))
        value = bond.value(float(row['Yield (%)'])/100)
        output.append(dict(row, Value=value['dirty']*quantity*rate,
                           DV01=value['dv01']*quantity*rate, Duration=value['modified'],
                           Convexity=value['convexity'], _bond=bond, _fx=rate))
    return output


def portfolio_risk(values):
    """Additive reporting-currency risk and normalized contributions for long holdings."""
    if not values:
        raise ValueError('Add at least one position.')
    table = pd.DataFrame([{k: v for k, v in p.items() if not k.startswith('_')} for p in values])
    total = table.Value.sum()
    dv01 = table.DV01.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError('Portfolio value must be positive and finite.')
    table['Weight (%)'] = table.Value / total * 100
    table['DV01 contribution (%)'] = table.DV01 / dv01 * 100 if dv01 else 0.
    table['Duration contribution (years)'] = table.Value / total * table.Duration
    table['Convexity contribution (years²)'] = table.Value / total * table.Convexity
    return table


def scenario_results(bond, ytm, scenarios):
    if not scenarios:
        raise ValueError('Add at least one named scenario.')
    names = set()
    base = float(price_grid(bond, ytm))
    output = []
    for row in scenarios:
        name = str(row['Name']).strip()
        if not name or name in names or len(name) > 100:
            raise ValueError('Scenario names must be unique, nonempty, and at most 100 characters.')
        names.add(name)
        benchmark, spread = float(row['Benchmark (bp)']), float(row['Spread (bp)'])
        if not np.all(np.isfinite([benchmark, spread])):
            raise ValueError('Scenario shocks must be finite.')
        shocked = ytm + (benchmark + spread) / 10000
        price = float(price_grid(bond, shocked))
        output.append({'Name':name, 'Benchmark (bp)':benchmark, 'Spread (bp)':spread,
                       'YTM (%)':shocked*100, 'Dirty price':price, 'P/L':price-base,
                       'Change (%)':(price/base-1)*100})
    return pd.DataFrame(output)


def portfolio_scenarios(values, scenarios):
    """Aggregate exact local bond repricing using unchanged explicit FX rates."""
    if not values:
        raise ValueError('Add portfolio holdings first.')
    total=sum(p['Value'] for p in values)
    result=None
    for position in values:
        table=scenario_results(position['_bond'],float(position['Yield (%)'])/100,scenarios)
        scale=float(position['Quantity'])*position['_fx']
        if result is None:
            result=table[['Name','Benchmark (bp)','Spread (bp)']].copy()
            result['Shocked value']=0.
            result['P/L']=0.
        result['Shocked value']+=table['Dirty price']*scale
        result['P/L']+=table['P/L']*scale
    result['Change (%)']=result['P/L']/total*100
    return result
