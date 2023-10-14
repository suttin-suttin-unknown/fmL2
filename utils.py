import configparser

def get_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config

def get_api_host():
    return get_config()["api"]["host"]

def get_data_root_dir():
    return get_config()["data"]["root"]

def convert_market_value(mv):
    if not mv:
        return None
    suffixes = {"K": 1000, "M": 1000000}
    suffix = mv[-1].upper()
    if suffix in suffixes:
        value = float(mv[:-1].strip("€"))
        return int(value * suffixes[suffix])
