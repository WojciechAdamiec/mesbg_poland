import json
import os
from os import PathLike
from battle import Battle


DATA_DIRECTORY = "data"
DB_FILE = os.path.join(DATA_DIRECTORY, "battles.json")


class BattleDB:
    def __init__(self, path: str | PathLike = DB_FILE):
        self.path = path
        self.battles: list[Battle] = []
        self.load()

    def remove_duplicates(self):
        unique_battles = {}
        for battle in self.battles:
            key = (
                battle.army_1_id,
                battle.army_2_id,
                battle.player_1_id,
                battle.player_2_id,
                battle.tournament_id,
            )
            if key not in unique_battles:
                unique_battles[key] = battle
        self.battles = list(unique_battles.values())

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.battles = [Battle.from_dict(b) for b in data]
        except (FileNotFoundError, json.JSONDecodeError):
            self.battles = []

    def save(self):
        self.remove_duplicates()
        dir_name = os.path.dirname(self.path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.battles], f, indent=4)
