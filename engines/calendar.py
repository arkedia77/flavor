"""절기 기반 월주 + JDN 기반 일주 계산"""

from engines.saju_tables import MONTH_TERM_TABLE


def jdn(year: int, month: int, day: int) -> int:
    """Julian Day Number 계산 (Gregorian calendar)"""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return (day + (153 * m + 2) // 5 + 365 * y
            + y // 4 - y // 100 + y // 400 - 32045)


def get_month_branch(month: int, day: int) -> int:
    """절기 기준 월지 인덱스 결정"""
    for g_month, cutoff, before, after in MONTH_TERM_TABLE:
        if g_month == month:
            return before if day < cutoff else after
    return 0


def hour_to_branch(hour: int) -> int:
    """시간(0~23) → 지지 인덱스 (자시=0, 축시=1, ...)"""
    h = 0 if hour == 23 else hour
    return (h + 1) // 2 % 12
