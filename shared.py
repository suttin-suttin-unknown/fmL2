def convert_price_string(ps):
    try:
        value = ps.strip('€')
        suffix = value[-1]
        value = float(value[0:-1])
        if suffix == 'm':
            value *= 1000000
        elif suffix == 'k':
            value *= 1000
        return value
    except:
        return None
