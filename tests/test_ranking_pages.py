import unittest
from importlib import import_module

import dash

import app
from store import load_main_ranking, load_master_ranking, load_online_ranking


class RankingPagesTests(unittest.TestCase):
    def test_year_sections_link_to_registered_pages(self):
        sections = {link.label: link for link in app.nav.children}
        registered_paths = {page["path"] for page in dash.page_registry.values()}
        for year in (2026, 2027):
            links = sections[f"{year} Rankings"].children
            self.assertEqual(
                [link.href for link in links],
                [f"/ranking_{kind}_{year}" for kind in ("main", "master", "online")],
            )
            for link in links:
                self.assertIn(link.href, registered_paths)

    def test_2027_ranking_tables(self):
        pages = {page["path"]: page for page in dash.page_registry.values()}
        loaders = {
            "main": load_main_ranking,
            "master": load_master_ranking,
            "online": load_online_ranking,
        }
        for kind, load in loaders.items():
            with self.subTest(kind=kind):
                old_layout = pages[f"/ranking_{kind}_2026"]["layout"]
                new_layout = pages[f"/ranking_{kind}_2027"]["layout"]
                old_table = old_layout.children[3].children
                new_table = new_layout.children[3].children
                old_headers = [cell.children for cell in old_table.children[0].children.children]
                new_headers = [cell.children for cell in new_table.children[0].children.children]
                if kind == "master":
                    self.assertEqual(new_headers, [
                        "Place", "Score", "Tie Breaker", "Display Name", "City Name",
                        "Master 1", "Master 2", "Master 3",
                    ])
                elif kind == "main":
                    self.assertEqual(new_headers, [
                        "Place", "Score", "Display Name", "City Name",
                        "Master Total", *[f"Master {i}" for i in range(1, 7)],
                        "Local Total", *[f"Local {i}" for i in range(1, 7)],
                    ])
                else:
                    self.assertEqual(new_headers, [
                        "Place", "Score", "Display Name", "City Name",
                        *[f"Online {i}" for i in range(1, 6)],
                    ])
                self.assertEqual(len(old_table.children[1].children), len(load()))
                name_index = new_headers.index("Display Name")
                names = [row.children[name_index].children for row in new_table.children[1].children]
                self.assertTrue(names)
                self.assertTrue(all(name.startswith("Sample:") for name in names))
                self.assertEqual(old_layout.children[0].children, f"2026 {kind.capitalize()} Ranking")
                self.assertEqual(new_layout.children[0].children, f"2027 {kind.capitalize()} Ranking")

    def test_2027_main_highlights(self):
        from pages.main_ranking_2027 import COLUMNS, HIGHLIGHT_FULL, HIGHLIGHT_HALF, HIGHLIGHT_ZERO, cell_style

        for key, _, align in COLUMNS:
            with self.subTest(key=key):
                self.assertEqual(cell_style(key, 0, align), {"textAlign": align, **HIGHLIGHT_ZERO})
        for key, value, expected in (
            ("master_challenger_1", 39, {}),
            ("master_challenger_1", 40, HIGHLIGHT_HALF),
            ("master_challenger_6", 59, HIGHLIGHT_HALF),
            ("master_challenger_6", 60, HIGHLIGHT_FULL),
            ("local_1", 19, {}),
            ("local_6", 20, HIGHLIGHT_FULL),
            ("master_challenger_total", 59, {}),
            ("master_challenger_total", 359, {}),
            ("master_challenger_total", 360, HIGHLIGHT_FULL),
            ("score", 479, {}),
            ("score", 480, HIGHLIGHT_FULL),
            ("local_total", 119, {}),
            ("local_total", 120, HIGHLIGHT_FULL),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(cell_style(key, value, "center"), {"textAlign": "center", **expected})

    def test_2027_main_rows_use_new_columns_and_highlights(self):
        from pages.main_ranking_2026 import make_layout
        from pages.main_ranking_2027 import COLUMNS, HIGHLIGHT_HALF, cell_style

        row = {key: 0 for key, _, _ in COLUMNS}
        row.update(displayName="Player", city_name="City", master_challenger_6=40)
        layout = make_layout([row], year=2027, rules=[], columns=COLUMNS, style_for_cell=cell_style)
        table = layout.children[3].children
        cells = table.children[1].children[0].children
        index = [key for key, _, _ in COLUMNS].index("master_challenger_6")
        self.assertEqual(cells[index].children, 40)
        self.assertEqual(cells[index].style, {"textAlign": "center", **HIGHLIGHT_HALF})

    def test_2027_main_sample_rows_cover_highlight_boundaries(self):
        from pages.main_ranking_2027 import sample_data

        self.assertEqual({row["master_challenger_total"] for row in sample_data}, {0, 138, 359, 360})
        self.assertEqual({row["local_total"] for row in sample_data}, {0, 39, 119, 120})
        self.assertEqual(
            {row[f"master_challenger_{i}"] for row in sample_data for i in range(1, 7)},
            {0, 39, 40, 59, 60},
        )
        self.assertEqual(
            {row[f"local_{i}"] for row in sample_data for i in range(1, 7)},
            {0, 19, 20},
        )

    def test_2027_online_columns_and_highlights(self):
        from pages.online_ranking_2026 import make_layout
        from pages.online_ranking_2027 import COLUMNS, HIGHLIGHT_FULL, HIGHLIGHT_ZERO, cell_style

        for key, value, expected in (
            ("online_1", 0, HIGHLIGHT_ZERO),
            ("online_1", 39, {}),
            ("online_1", 40, HIGHLIGHT_FULL),
            ("online_5", 40, HIGHLIGHT_FULL),
            ("score", 0, HIGHLIGHT_ZERO),
            ("score", 199, {}),
            ("score", 200, HIGHLIGHT_FULL),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(cell_style(key, value, "center"), {"textAlign": "center", **expected})

        row = {key: 0 for key, _, _ in COLUMNS}
        row.update(displayName="Player", city_name="City", score=200, online_5=40)
        layout = make_layout([row], year=2027, rules=[], columns=COLUMNS, style_for_cell=cell_style)
        cells = layout.children[3].children.children[1].children[0].children
        keys = [key for key, _, _ in COLUMNS]
        for key in ("score", "online_5"):
            self.assertEqual(cells[keys.index(key)].style, {"textAlign": "center", **HIGHLIGHT_FULL})

    def test_2027_online_sample_rows_cover_highlight_boundaries(self):
        from pages.online_ranking_2027 import sample_data

        self.assertEqual({row["score"] for row in sample_data}, {0, 89, 199, 200})
        self.assertEqual(
            {row[f"online_{i}"] for row in sample_data for i in range(1, 6)},
            {0, 10, 39, 40},
        )

    def test_2027_master_highlights_and_sample_rows(self):
        from pages.master_ranking_2027 import HIGHLIGHT_FULL, HIGHLIGHT_HALF, HIGHLIGHT_ZERO, cell_style, sample_data

        for key, value, expected in (
            ("master_1", 0, HIGHLIGHT_ZERO),
            ("master_1", 39, {}),
            ("master_1", 40, HIGHLIGHT_HALF),
            ("master_3", 59, HIGHLIGHT_HALF),
            ("master_3", 60, HIGHLIGHT_FULL),
            ("score", 179, {}),
            ("score", 180, HIGHLIGHT_FULL),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(cell_style(key, value, "center"), {"textAlign": "center", **expected})
        self.assertEqual({row["score"] for row in sample_data}, {0, 138, 179, 180})
        self.assertEqual(
            {row[f"master_{i}"] for row in sample_data for i in range(1, 4)},
            {0, 39, 40, 59, 60},
        )

    def test_rules_are_collapsed_and_use_each_page_content(self):
        pages = {page["path"]: page for page in dash.page_registry.values()}
        for year in (2026, 2027):
            for kind in ("main", "master", "online"):
                with self.subTest(year=year, kind=kind):
                    layout = pages[f"/ranking_{kind}_{year}"]["layout"]
                    rules = layout.children[1]
                    self.assertFalse(getattr(rules, "open", False))
                    self.assertEqual(rules.children[0].children.children, "Rules")
                    content = rules.children[1].children
                    self.assertEqual(content, import_module(f"ranking_rules.{kind}_{year}").RULES)

    def test_2026_online_individual_tournament_examples(self):
        from ranking_rules.online_2026 import RULES

        tables = [component.data for component in RULES if component.__class__.__name__ == "Table"]
        self.assertEqual(tables, [
            {"head": ["Place", *range(1, 14)],
             "body": [["Points", 13, 12, 11, 10, 9, 8, 7, 6, 5, 5, 5, 5, 5]]},
            {"head": ["Place", *range(1, 9)],
             "body": [["Points", 8, 7, 6, 5, 5, 5, 5, 5]]},
        ])

    def test_2026_main_tournament_points(self):
        from ranking_rules.main_2026 import RULES

        tables = [component.children.data for component in RULES
                  if component.__class__.__name__ == "ScrollArea"]
        self.assertEqual(tables, [
            {"head": ["Place", 1, 2, 3, 4, 5, 6, 7, 8, "9+"],
             "body": [["Points", 20, 18, 16, 15, 14, 13, 12, 11, 10]]},
            {"head": ["Place", *range(1, 27), "27+"],
             "body": [["Points", 40, 37, 34, 33, 32, 31, 30, 29, 28, 27, 26, 25, 24, 23, 22,
                       21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10]]},
            {"head": ["Place", *range(1, 36), "36+"],
             "body": [["Points", 60, 55, 50, 48, 46, 44, 42, 40, 38, 36, 35, 34, 33, 32, 31, 30,
                       29, 28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10]]},
            {"head": ["Place", *range(1, 20), "20+"],
             "body": [["Points", 60, 55, 50, 47, 44, 41, 38, 35, 32, 29, 27, 25, 23, 21, 19, 17, 15, 13, 11, 10]]},
        ])

    def test_2027_main_scoring_tables(self):
        from ranking_rules.main_2026 import RULES as rules_2026
        from ranking_rules.main_2027 import RULES as rules_2027

        old_tables = [item.children.data for item in rules_2026 if item.__class__.__name__ == "ScrollArea"]
        new_tables = [item.children.data for item in rules_2027 if item.__class__.__name__ == "ScrollArea"]
        self.assertEqual(new_tables[:3], old_tables[:3])
        self.assertEqual(new_tables[3], {
            "head": ["Place", *range(1, 18), "18+"],
            "body": [["Points", 60, 50, 45, 42, 39, 36, 33, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10]],
        })
        self.assertIn("top6 Master or Challenger", rules_2027[0].children)
        self.assertIn("top6 Local", rules_2027[0].children)

    def test_2027_master_rules_use_main_scoring_without_dmp(self):
        from ranking_rules.main_2027 import RULES as main_rules
        from ranking_rules.master_2027 import RULES as master_rules

        main_tables = [item.children.data for item in main_rules if item.__class__.__name__ == "ScrollArea"]
        master_tables = [item.children.data for item in master_rules if item.__class__.__name__ == "ScrollArea"]
        self.assertEqual(master_tables, main_tables[1:])
        self.assertIn("three best Master or Challenger", master_rules[0].children)
        self.assertIn("DMP does not count", master_rules[0].children)

    def test_2027_online_tournament_points(self):
        from ranking_rules.online_2027 import RULES

        tables = [item.children.data for item in RULES if item.__class__.__name__ == "ScrollArea"]
        self.assertEqual(tables, [
            {"head": ["Place", *range(1, 17), "17+"],
             "body": [["Points", 40, 35, 31, 28, 26, 24, 22, 20, 18, 17, 16, 15, 14, 13, 12, 11, 10]]},
            {"head": ["Place", *range(1, 9), "9+"],
             "body": [["Points", 40, 31, 26, 22, 18, 16, 14, 12, 10]]},
        ])


if __name__ == "__main__":
    unittest.main()
