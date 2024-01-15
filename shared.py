def convert_price_string(ps):
    value = ps.strip('€')
    suffix = value[-1]
    value = float(value[0:-1])
    if suffix == 'm':
        value *= 1000000
    elif suffix == 'k':
        value *= 1000
    return value


def get_years_and_months(d1, d2):
    if d1 > d2:
        d1, d2 = d2, d1

    years = d2.year - d1.year

    if (d2.month < d1.month) or (d2.month == d1.month and d2.day < d1.day):
        years -= 1

    months = d2.month - d1.month
    if months < 0:
        months += 12

    if d2.day < d1.day:
        months -= 1
        if months < 0:
            months = 11

    return years, months
