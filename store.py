import json
import os
from download_data import (
    DATA_DIRECTORY,
    MAIN_RANKING_FILE,
    ONLINE_RANKING_FILE,
    MASTER_RANKING_FILE,
    MASTER_TOURNAMENTS_FILE,
    BATTLES_FILE,
    ARMIES_FILE,
)


def load_main_ranking():
    main_ranking_path = os.path.join(DATA_DIRECTORY, MAIN_RANKING_FILE)
    if not os.path.exists(main_ranking_path):
        return []
    with open(main_ranking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_online_ranking():
    online_ranking_path = os.path.join(DATA_DIRECTORY, ONLINE_RANKING_FILE)
    if not os.path.exists(online_ranking_path):
        return []
    with open(online_ranking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_master_ranking():
    master_ranking_path = os.path.join(DATA_DIRECTORY, MASTER_RANKING_FILE)
    if not os.path.exists(master_ranking_path):
        return []
    with open(master_ranking_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_master_tournaments():
    master_tournaments_path = os.path.join(DATA_DIRECTORY, MASTER_TOURNAMENTS_FILE)
    if not os.path.exists(master_tournaments_path):
        return []
    with open(master_tournaments_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_battles():
    battles_path = os.path.join(DATA_DIRECTORY, BATTLES_FILE)
    if not os.path.exists(battles_path):
        return []
    with open(battles_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_armies():
    armies_path = os.path.join(DATA_DIRECTORY, ARMIES_FILE)
    if not os.path.exists(armies_path):
        return []
    with open(armies_path, "r", encoding="utf-8") as f:
        return json.load(f)