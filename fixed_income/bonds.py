"""Regular, maturity-anchored coupon schedules with no business-day adjustment.

Yields are nominal annual rates compounded at coupon frequency. Settlement on a
coupon date excludes that coupon. Prices are currency amounts for the entire face.
"""
from dataclasses import dataclass
from datetime import date
import calendar
import math

import numpy as np
import pandas as pd
from scipy.optimize import brentq

CONVENTIONS = ('ACT/ACT ICMA', 'ACT/365F', 'ACT/360', '30E/360')


def shift_months(anchor: date, months: int) -> date:
    """Preserve maturity's day, including end-of-month, without iterative drift."""
    total = anchor.year * 12 + anchor.month - 1 + months
    year, month0 = divmod(total, 12)
    month = month0 + 1
    last = calendar.monthrange(year, month)[1]
    eom = anchor.day == calendar.monthrange(anchor.year, anchor.month)[1]
    return date(year, month, last if eom else min(anchor.day, last))


def year_fraction(start: date, end: date, convention: str,
                  period_start: date | None = None, period_end: date | None = None,
                  frequency: int = 2) -> float:
    if convention not in CONVENTIONS:
        raise ValueError('Unsupported day-count convention')
    days = (end - start).days
    if convention == 'ACT/365F':
        return days / 365
    if convention == 'ACT/360':
        return days / 360
    if convention == '30E/360':
        return ((end.year-start.year)*360 + (end.month-start.month)*30
                + min(end.day, 30)-min(start.day, 30)) / 360
    if period_start is None or period_end is None or period_end <= period_start:
        raise ValueError('ACT/ACT ICMA requires a valid reference coupon period')
    return days / ((period_end-period_start).days * frequency)


@dataclass(frozen=True)
class Bond:
    face: float
    coupon: float
    maturity: date
    settlement: date
    frequency: int = 2
    day_count: str = 'ACT/ACT ICMA'

    def __post_init__(self):
        if not math.isfinite(self.face) or self.face <= 0:
            raise ValueError('Face value must be finite and positive')
        if not math.isfinite(self.coupon) or self.coupon < 0:
            raise ValueError('Coupon rate must be finite and nonnegative')
        if self.frequency not in (1, 2, 4):
            raise ValueError('Coupon frequency must be 1, 2, or 4')
        if self.settlement >= self.maturity:
            raise ValueError('Settlement must precede maturity')
        if self.day_count not in CONVENTIONS:
            raise ValueError('Unsupported day-count convention')
        if (self.maturity-self.settlement).days > 365 * 100:
            raise ValueError('Maximum supported remaining term is 100 years')

    def schedule(self) -> list[date]:
        dates = [self.maturity]
        k = 1
        while dates[-1] > self.settlement:
            dates.append(shift_months(self.maturity, -k * (12 // self.frequency)))
            k += 1
        return list(reversed(dates))

    @property
    def accrued(self) -> float:
        dates = self.schedule()
        fraction = year_fraction(dates[0], self.settlement, self.day_count,
                                 dates[0], dates[1], self.frequency)
        return self.face * self.coupon * fraction

    def cashflows(self) -> pd.DataFrame:
        dates = self.schedule()
        # ICMA accumulates reference-period fractions, so regular coupon dates
        # are exactly one period apart even across leap years.
        elapsed = year_fraction(dates[0], self.settlement, self.day_count,
                                dates[0], dates[1], self.frequency)
        rows = []
        time = -elapsed
        for previous, payment in zip(dates, dates[1:]):
            time += year_fraction(previous, payment, self.day_count,
                                  previous, payment, self.frequency)
            coupon = self.face * self.coupon / self.frequency
            principal = self.face if payment == self.maturity else 0.0
            rows.append((payment, time, coupon, principal, coupon + principal))
        return pd.DataFrame(rows, columns=['Payment date', 'Time (years)',
                                          'Coupon', 'Principal', 'Cash flow'])

    def value(self, ytm: float) -> dict:
        if not math.isfinite(ytm) or ytm <= -self.frequency:
            raise ValueError('Yield must exceed minus the coupon frequency')
        flows = self.cashflows()
        t = flows['Time (years)'].to_numpy()
        base = 1 + ytm/self.frequency
        with np.errstate(over='ignore'):
            factors = np.exp(-self.frequency*t*np.log(base))
        flows['Discount factor'] = factors
        flows['PV coupon'] = flows['Coupon'] * factors
        flows['PV principal'] = flows['Principal'] * factors
        flows['Present value'] = flows['Cash flow'] * factors
        pv = flows['Present value'].to_numpy()
        price = float(pv.sum())
        if not np.isfinite(price) or price <= 0:
            raise ValueError('Yield produces a price outside numerical range')
        macaulay = float(np.dot(t, pv) / price)
        modified = macaulay/base
        convexity = float(np.dot(t*(t+1/self.frequency), pv) / (price*base**2))
        return dict(dirty=price, clean=price-self.accrued, accrued=self.accrued,
                    macaulay=macaulay, modified=modified,
                    dollar_duration=price*modified, dv01=price*modified*1e-4,
                    convexity=convexity, nominal=float(flows['Cash flow'].sum()),
                    pv_coupons=float(flows['PV coupon'].sum()),
                    pv_principal=float(flows['PV principal'].sum()), flows=flows)

    def yield_from_price(self, price: float, price_type: str = 'Clean') -> float:
        if price_type not in ('Clean', 'Dirty'):
            raise ValueError('Price type must be Clean or Dirty')
        if not math.isfinite(price) or price <= 0:
            raise ValueError('Market price must be finite and positive')
        target = price + self.accrued if price_type == 'Clean' else price
        flows = self.cashflows()
        times = flows['Time (years)'].to_numpy() * self.frequency
        amounts = flows['Cash flow'].to_numpy()
        # Solve in log(1+y/f) space; this retains the entire negative-yield
        # domain and avoids evaluating overflowing prices during bracketing.
        from scipy.special import logsumexp
        def residual(log_base):
            return float(logsumexp(np.log(amounts[amounts > 0])
                         - times[amounts > 0]*log_base) - np.log(target))
        low, high = -1.0, 1.0
        while residual(low) < 0:
            low *= 2
        while residual(high) > 0:
            high *= 2
        root = brentq(residual, low, high, xtol=1e-14)
        result = self.frequency * math.expm1(root)
        if not math.isfinite(result) or result <= -self.frequency:
            raise ValueError('Implied yield lies outside representable range')
        return result
