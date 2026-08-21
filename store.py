

import json
import os

from download_data import DATA_DIRECTORY, MAIN_RANKING_FILE, ONLINE_RANKING_FILE


def load_main_ranking():
    main_ranking_path = os.path.join(DATA_DIRECTORY, MAIN_RANKING_FILE)
    if not os.path.exists(main_ranking_path):
        return []
    with open(main_ranking_path, "r") as f:
        return json.load(f)


def load_online_ranking():
    online_ranking_path = os.path.join(DATA_DIRECTORY, ONLINE_RANKING_FILE)
    if not os.path.exists(online_ranking_path):
        return []
    with open(online_ranking_path, "r") as f:
        return json.load(f)