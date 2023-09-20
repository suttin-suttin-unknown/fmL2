import json

def get_countries():
    with open("countries.json", "r") as f:
        return json.load(f)

if __name__ == "__main__":
    countries = get_countries_info()
    print(info)
