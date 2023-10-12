import configparser

def get_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config

def get_api_host():
    return get_config()["api"]["host"]

def get_data_root_dir():
    return get_config()["data"]["root"]