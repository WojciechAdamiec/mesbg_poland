from datetime import datetime
from battle import Patch


PATCH_DATES = {
    datetime.strptime("01-12-2025", "%d-%m-%Y").date(): Patch.BALROG,
    datetime.strptime("19-02-2026", "%d-%m-%Y").date(): Patch.GWAIHIR,
    datetime.strptime("02-07-2026", "%d-%m-%Y").date(): Patch.NIGHTLINGS
}


def select_patch(event_date: datetime.date) -> Patch:
    sorted_dates = sorted(PATCH_DATES.keys())
    selected_patch = None

    for date in sorted_dates:
        if event_date >= date:
            selected_patch = PATCH_DATES[date]
        else:
            break

    return selected_patch