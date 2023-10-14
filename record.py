import api
from utils import convert_market_value

import math
from datetime import datetime

from abc import ABC, abstractmethod
from itertools import chain
from operator import itemgetter


class Record(ABC):
    _api_json = {}

    def __init__(self, id):
        self.id = id

    @classmethod
    @abstractmethod
    def from_api(cls, id):
        pass


class League(Record):
    @classmethod
    def from_api(cls, id):
        league = cls(id)
        league._api_json = api.get_league(id)
        return league
    
    @property
    def _details(self):
        return self._api_json["details"]
    
    @property
    def name(self):
        return self._details["name"]
    
    @property
    def country(self):
        return self._details["country"]
    
    @property
    def latest_season(self):
        return self._details["latestSeason"]
    
    @property
    def stat_links(self):
        return [itemgetter(*["Name", "TotwRoundsLink"])(_) for _ in self._api_json["stats"]["seasonStatLinks"]]

    @property
    def team_ids(self):
        try:
            return list(set(team["id"] for team in self._api_json["table"][0]["data"]["table"]["all"]))
        except LookupError:
            return list(set(chain(*[[team["id"] for team in table["table"]["all"]] 
                                    for table in self._api_json["table"][0]["data"]["tables"]])))


class Player(Record):
    @classmethod
    def from_api(cls, id):
        player = cls(id)
        player._api_json = api.get_player(id)
        return player
    
    @property
    def _position_data(self):
        return self._api_json["origin"]["positionDesc"]["positions"]
    
    @property
    def _player_props(self):
        return dict([(prop["translationKey"], prop) for prop in self._api_json["playerProps"]])

    @property
    def _birth_date(self):
        return int(self._player_props["years"]["dateOfBirth"]["utcTime"] / 1000)

    @property
    def _country(self):
        return self._player_props["country_sentencecase"]["countryCode"]
    
    @property
    def _market_value(self):
        return self._player_props["transfer_value"]["value"]["fallback"]

    @property
    def name(self):
        return self._api_json["name"]
    
    @property
    def positions(self):
        positions = sorted(self._position_data, key=lambda d: -d["isMainPosition"])
        return [(p["strPosShort"]["label"], p["occurences"]) for p in positions]
    
    @property
    def position_string(self):
        try:
            return "/".join(p[0] for p in self.positions)
        except LookupError:
            return ""

    @property
    def height(self):
        try:
            return int(self._player_props["height_sentencecase"]["value"]["fallback"].split()[0])
        except LookupError:
            return -1
        
    @property
    def birth_date(self):
        try:
            return self._birth_date
        except LookupError:
            return -1
        
    @property
    def country(self):
        try:
            return self._country
        except LookupError:
            return ""
        
    @property
    def market_value(self):
        try:
            return self._market_value
        except LookupError:
            return -1
        
    @property
    def _relative_age(self):
        if self.birth_date == -1:
            return -1
        return round((datetime.now() - datetime.fromtimestamp(self.birth_date)).days / 365.25, 2)
    
    @property
    def age(self):
        return math.floor(self._relative_age)
    
    @property
    def senior_appearances(self):
        try:
            apps = [item["appearances"] for item in self._api_json["careerHistory"]["careerData"]["careerItems"]["senior"] if item["appearances"]]
            return sum(int(app) for app in apps)
        except LookupError:
            return -1
        
    @property
    def total_minutes(self):
        seasons = list(chain(*[_["seasons"] for _ in self._api_json["careerStatistics"]]))
        stats = list(chain(*[[_["statsArr"] for _ in _["stats"]] for _ in seasons]))
        stats = list(chain(*[_ for _ in stats]))
        minutes = [int(_[-1]["value"]) for _ in stats if _[-1]["key"] == "minutes_played"]
        return sum(minutes)


class Team(Record):
    @classmethod
    def from_api(cls, id):
        team = cls(id)
        team._api_json = api.get_team(id)
        return team
    
    @property
    def _transfers(self):
        try:
            return list(chain(*self._api_json["transfers"]["data"].values()))
        except (LookupError, TypeError):
            return []

    @property
    def transfers(self):
        for transfer in self._transfers:
            info = {}
            for key in transfer:
                if key == "fee":
                    info[key] = transfer.get("fee") or -1
                elif type(transfer[key]) not in [dict, list]:
                    info[key] = transfer[key]
            
            if info["fee"] != -1:
                info["fee"] = convert_market_value(info["fee"].get("value")) or 0

            info["marketValue"] = convert_market_value(info.get("marketValue")) or -1
            try:
                del info["position"]
            except KeyError:
                pass

            yield info

    @property
    def contract_extensions(self):
        extra_keys = ["fromClub", "fromClubId", "toClub", "toClubId", "fee", "contractExtension", "onLoan"]
        for info in self.transfers:
            if info["contractExtension"]:
                for key in extra_keys:
                    try:
                        del info[key]
                    except KeyError:
                        continue
                yield info

    @property
    def transfers_in(self):
        extra_keys = ["toClub", "toClubId", "contractExtension"]
        for info in self.transfers:
            if not info["contractExtension"] and info["toClubId"] == self.id:
                for key in extra_keys:
                    try:
                        del info[key]
                    except KeyError:
                        continue
                yield info

    @property
    def transfers_out(self):
        extra_keys = ["fromClub", "fromClubId", "contractExtension"]
        for info in self.transfers:
            if not info["contractExtension"] and info["fromClubId"] == self.id:
                for key in extra_keys:
                    try:
                        del info[key]
                    except KeyError:
                        continue
                yield info
