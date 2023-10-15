import api
from utils import convert_market_value

import json
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
    def _player_props(self):
        return dict([(prop["translationKey"], prop) for prop in self._api_json["playerProps"]])
    
    @property
    def name(self):
        return self._api_json["name"]
    
    @property
    def market_value_string(self):
        return self._player_props["transfer_value"]["value"]["fallback"]

    @property
    def position_occurences(self):
        try:
            positions = sorted(self._api_json["origin"]["positionDesc"]["positions"], key=lambda d: -d["isMainPosition"])
            return dict([(p["strPosShort"]["label"], p["occurences"]) for p in positions])
        except TypeError:
            return None
    
    @property
    def positions(self):
        try:
            return list(self.position_occurences.keys())
        except AttributeError:
            return []
        
    @property
    def position_string(self):
        return "/".join(self.positions)
    
    @property
    def preferred_foot(self):
        try:
            return self._player_props["preferred_foot"]["value"]["fallback"]
        except KeyError:
            return ""
        
    @property
    def height_string(self):
        try:
            return self._player_props["height_sentencecase"]["value"]["fallback"]
        except KeyError:
            return ""

    @property
    def height(self):
        try:
            return int(self.height_string.split()[0])
        except (IndexError, TypeError, ValueError):
            return -1
        
    @property
    def birth_date(self):
        try:
            timestamp = int(self._player_props["years"]["dateOfBirth"]["utcTime"]/1000)
            return datetime.fromtimestamp(timestamp).date()
        except (KeyError, ValueError, AttributeError):
            return None
        
    @property
    def birth_date_string(self):
        return str(self.birth_date or "")
        
    @property
    def country(self):
        try:
            return self._player_props["country_sentencecase"]["countryCode"]
        except KeyError:
            return ""
        
    @property
    def market_value(self):
        try:
            return convert_market_value(self.market_value_string)
        except LookupError:
            return -1

    @property
    def full_age(self):
        days = (datetime.now().date() - self.birth_date).days
        years = days // 365
        days %= 365
        months = days // 30
        days %= 30
        return (years, months, days)

    @property
    def full_age_string(self):
        (years, months, days) = self.full_age
        sections = [f"{years} years"]
        if months != 0:
            sections.append(f"{months} months")
        if days != 0:
            sections.append(f"{days} days")
        return ", ".join(sections)
        
    @property
    def age(self):
        return self.full_age[0]
    
    @property
    def senior_appearances(self):
        try:
            apps = [_["appearances"] for _ in self._api_json["careerHistory"]["careerData"]["careerItems"]["senior"] if _["appearances"]]
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
