import api
from utils import convert_market_value

from abc import ABC, abstractmethod
from datetime import datetime
from itertools import chain
from operator import itemgetter


class Record(ABC, dict):
    @classmethod
    @abstractmethod
    def from_api(cls, id):
        pass


class Player(Record):
    @classmethod
    def from_api(cls, id):
        return cls(api.get_player(id))
    
    @property
    def _props(self):
        return dict([(prop["translationKey"], prop) for prop in self["playerProps"]])
    
    @property
    def id(self):
        return self["id"]

    @property
    def name(self):
        return self["name"]
    
    @property
    def team_id(self):
        return self["origin"]["teamId"]
    
    @property
    def team_name(self):
        return self["origin"]["teamName"]
    
    @property
    def country(self):
        return self._props["country_sentencecase"]["countryCode"]
    
    @property
    def market_value(self):
        try:
            return convert_market_value(self._props["transfer_value"]["value"]["fallback"])
        except KeyError:
            return -1
        
    @property
    def positions(self):
        return [_["strPosShort"]["label"] for _ in 
                sorted(self["origin"]["positionDesc"]["positions"], key=lambda d: -d["isMainPosition"])]
    
    @property
    def height(self):
        try:
            return int(self._props["height_sentencecase"]["value"]["fallback"].split()[0])
        except KeyError:
            return -1
        
    @property
    def birth_date(self):
        try:
            return datetime.fromtimestamp(int(self._props["years"]["dateOfBirth"]["utcTime"]/1000)).date()
        except KeyError:
            return None
        
    @property
    def age_full(self):
        days = (datetime.now().date() - self.birth_date).days
        years = days // 365
        days %= 365
        months = days // 30
        days %= 30
        return (years, days, months)
    
    @property
    def age(self):
        return self.age_full[0]
    
    @property
    def total_appearances(self):
        return sum(int(_["appearances"]) 
                   for _ in self["careerHistory"]["careerData"]["careerItems"]["senior"] if _["appearances"])

    @property
    def total_minutes(self):
        seasons = list(chain(*[_["seasons"] for _ in self["careerStatistics"]]))
        stats = list(chain(*[[_["statsArr"] for _ in _["stats"]] for _ in seasons]))
        stats = list(chain(*[_ for _ in stats]))
        minutes = [int(_[-1]["value"]) for _ in stats if _[-1]["key"] == "minutes_played"]
        return sum(minutes)


class League(Record):
    @classmethod
    def from_api(cls, id):
        return cls(api.get_league(id))
    
    @property
    def name(self):
        return self["details"]["name"]
    
    @property
    def country(self):
        return self["details"]["country"]
    
    @property
    def latest_season(self):
        return self["details"]["latestSeason"]
    
    @property
    def stats_links(self):
        return [itemgetter(*["Name", "TotwRoundsLink"])(_) for _ in self["stats"]["seasonStatLinks"]]
    
    @property
    def team_ids(self):
        try:
            return list(set(_["id"] for _ in self["table"][0]["data"]["table"]["all"]))
        except LookupError:
            return list(set(chain(*[[_["id"] for _ in _["table"]["all"]] 
                                    for _ in self["table"][0]["data"]["tables"]])))


class Team(Record):
    @classmethod
    def from_api(cls, id):
        return cls(api.get_team(id))
    
    @property
    def id(self):
        return self["details"]["id"]
    
    @property
    def name(self):
        return self["details"]["name"]
    
    @property
    def transfers_in(self):
        return self["transfers"]["data"]["Players in"]
    
    @property
    def transfers_out(self):
        return self["transfers"]["data"]["Players out"]
    
    @property
    def contract_extensions(self):
        return self["transfers"]["data"]["Contract extension"]




