from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Points:
    value: int
    doubled: bool = False

    @property
    def total(self):
        return self.value * (2 if self.doubled else 1)


class TournamentType(Enum):
    LOCAL = 1
    CHALLENGER = 2
    MASTER = 3
    DMP = 4
    ONLINE = 5


class Patch(Enum):
    BALROG = 1
    GWAIHIR = 2
    NIGHTLINGS = 3


class Scenario(Enum):
    DOMINATION = "Domination"
    TO_THE_DEATH = "To The Death!"
    HOLD_GROUND = "Hold Ground"
    DESTROY_THE_SUPPLIES = "Destroy the Supplies"
    RECONNOITRE = "Reconnoitre"
    FOG_OF_WAR = "Fog of War"
    CAPTURE_AND_CONTROL = "Capture & Control"
    BREAKTHROUGH = "Breakthrough"
    STAKE_A_CLAIM = "Stake a Claim"
    LORDS_OF_BATTLE = "Lords of Battle"
    ASSASSINATION = "Assassination"
    CONTEST_OF_CHAMPIONS = "Contest of Champions"
    HEIRLOOM_OF_AGES_PAST = "Heirloom of Ages Past"
    SITES_OF_POWER = "Sites of Power"
    COMMAND_THE_BATTLEFIELD = "Command the Battlefield"
    RETRIEVAL = "Retrieval"
    SEIZE_THE_PRIZES = "Seize the Prizes"
    TREASURE_HOARD = "Treasure Hoard"
    STORM_THE_CAMP = "Storm the Camp"
    DIVIDE_AND_CONQUER = "Divide & Conquer"
    ESCORT_THE_WOUNDED = "Escort the Wounded"
    CLASH_BY_MOONLIGHT = "Clash by Moonlight"
    LEAD_FROM_THE_FRONT = "Lead From the Front"
    CONVERGENCE = "Convergence"

@dataclass
class Battle:
    result: tuple[int, int]
    player_1_id: str | int
    player_2_id: str | int
    player_1_name: str
    player_2_name: str
    patch: Patch | None = None
    army_1_id: int | None = None
    army_2_id: int | None = None
    army_1_name: str | None = None
    army_2_name: str | None = None
    points: Points | None = None
    scenario: Scenario | None = None
    tournament_id: str | None = None
    tournament_name: str | None = None
    tournament_type: TournamentType | None = None

    def to_dict(self) -> dict:
        return {
            "points": {
                "value": self.points.value,
                "doubled": self.points.doubled,
            } if self.points else None,
            "army_1_id": self.army_1_id if self.army_1_id is not None else None,
            "army_2_id": self.army_2_id if self.army_2_id is not None else None,
            "army_1_name": self.army_1_name if self.army_1_name is not None else None,
            "army_2_name": self.army_2_name if self.army_2_name is not None else None,
            "scenario": self.scenario.name if self.scenario else None,
            "result": self.result,
            "patch": self.patch.name if self.patch else None,
            "tournament_id": self.tournament_id,
            "tournament_name": self.tournament_name,
            "tournament_type": self.tournament_type.name if self.tournament_type else None,
            "player_1_id": self.player_1_id,
            "player_2_id": self.player_2_id,
            "player_1_name": self.player_1_name,
            "player_2_name": self.player_2_name,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Battle":
        return cls(
            points=Points(
                value=data["points"]["value"],
                doubled=data["points"].get("doubled", False),
            ) if data.get("points") else None,
            army_1_id=data.get("army_1_id"),
            army_2_id=data.get("army_2_id"),
            army_1_name=data.get("army_1_name"),
            army_2_name=data.get("army_2_name"),
            scenario=Scenario[data["scenario"]] if data.get("scenario") else None,
            result=tuple(data["result"]) if data.get("result") is not None else None,
            patch=Patch[data["patch"]] if data.get("patch") else None,
            tournament_id=data.get("tournament_id"),
            tournament_name=data.get("tournament_name"),
            tournament_type=TournamentType[data["tournament_type"]] if data.get("tournament_type") else None,
            player_1_id=data["player_1_id"],
            player_2_id=data["player_2_id"],
            player_1_name=data["player_1_name"],
            player_2_name=data["player_2_name"],
        )
