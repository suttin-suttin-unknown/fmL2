import api

from abc import ABC, abstractmethod
from itertools import chain


class Record(ABC):
    _api_json = {}

    def __init__(self, id, api_json):
        self.id = id
        self._api_json = api_json

    @classmethod
    @abstractmethod
    def from_api(cls, id):
        pass


class League(Record):
    @classmethod
    def from_api(cls, id):
        return cls(id, api.get_league(id))
    
    @property
    def details(self):
        return self._api_json["details"]
    
    @property
    def name(self):
        return self.details["name"]
    
    @property
    def country(self):
        return self.details["country"]
    
    @property
    def latest_season(self):
        return self.details["latestSeason"]
    
    @property
    def stat_links(self):
        for item in self._api_json["stats"]["seasonStatLinks"]:
            yield {"name": item["Name"], "link": item["TotwRoundsLink"]}

    @property
    def teams(self):
        try:
            return list(set(team["id"] for team in self._api_json["table"][0]["data"]["table"]["all"]))
        except LookupError:
            return list(set(chain(*[[team["id"] for team in table["table"]["all"]] 
                                    for table in self._api_json["table"][0]["data"]["tables"]])))
