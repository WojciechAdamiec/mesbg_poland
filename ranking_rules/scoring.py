import dash_mantine_components as dmc


LOCAL = (
    [1, 2, 3, 4, 5, 6, 7, 8, "9+"],
    [20, 18, 16, 15, 14, 13, 12, 11, 10],
)
CHALLENGER = (
    [*range(1, 27), "27+"],
    [40, 37, 34, *range(33, 9, -1)],
)
MASTER_INDIVIDUAL = (
    [*range(1, 36), "36+"],
    [60, 55, 50, 48, 46, 44, 42, 40, 38, 36, 35, 34, 33, 32, 31, 30, 29, 28,
     27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10],
)
MASTER_PAIRS_2027 = (
    [*range(1, 18), "18+"],
    [60, 50, 45, 42, 39, 36, 33, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10],
)
ONLINE_INDIVIDUAL_2027 = (
    [*range(1, 17), "17+"],
    [40, 35, 31, 28, 26, 24, 22, 20, 18, 17, 16, 15, 14, 13, 12, 11, 10],
)
ONLINE_TEAM_2027 = (
    [*range(1, 9), "9+"],
    [40, 31, 26, 22, 18, 16, 14, 12, 10],
)


def scoring_table(places, points):
    return dmc.ScrollArea(
        dmc.Table(
            data={"head": ["Place", *places], "body": [["Points", *points]]},
            withTableBorder=True,
            withColumnBorders=True,
        ),
        type="auto",
        scrollbars="x",
        offsetScrollbars=True,
    )
