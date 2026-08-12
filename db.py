import json
from os import PathLike
from battle import Battle


DB_FILE = "battles.json"


class BattleDB:
    def __init__(self, path: str | PathLike):
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
        except FileNotFoundError:
            self.battles = []

    def save(self):
        self.remove_duplicates()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.battles], f, indent=4)
