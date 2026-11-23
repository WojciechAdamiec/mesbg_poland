import unittest

from dash import html

import tags
from articles import render_body


class TagTests(unittest.TestCase):
    def test_tag_files_are_typed_and_contain_requested_items(self):
        self.assertEqual(tags.TAG_TYPES, ("army_lists", "players", "places", "tournaments"))
        self.assertTrue(tags.has_tag("army_lists", "rohan", 336))
        self.assertTrue(tags.has_tag("army_lists", "rohan", 461))
        self.assertFalse(tags.has_tag("army_lists", "rohan", 347))
        self.assertTrue(tags.has_tag("army_lists", "good-men", 347))
        self.assertTrue(tags.has_tag("players", "coordinators", "dd081a04-8bbb-4409-aed7-f6ceedf4d7d0"))
        self.assertTrue(tags.has_tag("places", "silesia", 3189))
        self.assertFalse(tags.has_tag("army_lists", "rohan", 468))
        self.assertEqual(tags.load_tags("tournaments"), ())

    def test_unknown_types_and_tag_references_raise_clear_errors(self):
        with self.assertRaisesRegex(ValueError, "Unknown tag type"):
            tags.load_tags("characters")
        with self.assertRaisesRegex(KeyError, "Unknown players tag"):
            tags.get_tag("players", "missing")
        with self.assertRaisesRegex(KeyError, "Unknown army_lists tag"):
            tags.render_tagged_text("[[tag:army_lists:missing]]")

    def test_coordinators_tag_contains_members_and_lists_them_in_tooltip(self):
        tag = tags.get_tag("players", "coordinators")
        self.assertEqual(tag.name, "Coordinators")
        self.assertEqual(tag.items, (
            "7fa5ba4b-28df-44e8-a4f2-d87072e98a2b",
            "55b3019a-a7e5-4c3c-9c51-0643513d2296", "708078fa-6770-4b38-a508-7bee7d0b95a2",
            "396741ce-3694-4877-9603-fe19efd6284f", "dd081a04-8bbb-4409-aed7-f6ceedf4d7d0",
        ))
        tooltip = tags.render_tagged_text("[[tag:players:coordinators]]").children[0].label
        self.assertEqual([line.children for line in tooltip.children[1].children if line.children],
                         ["Bakson", "FishPriest", "Gadii", "Kacik", "Shogun"])

    def test_representatives_tag_contains_members_and_lists_them_in_tooltip(self):
        tag = tags.get_tag("players", "representatives")
        self.assertEqual(tag.items, (
            "1857125d-c4f2-4a84-a26c-18ff4acbbcaf",
            "d0cc3137-fab5-4977-bfac-cf0a791bd9b0",
            "06e08db4-eeb0-41a3-9e0c-7a8d0203bc0e",
            "610dd47d-893e-4d57-965f-8f813c4f235c",
            "4a654798-2e4f-4961-9daa-76818d5f169e",
            "780e8297-2cf1-4ac2-89bd-e9dd5ece6347",
            "224b8d3d-7e1f-4095-853a-088883879195",
        ))
        tooltip = tags.render_tagged_text("[[tag:players:representatives]]").children[0].label
        self.assertEqual([line.children for line in tooltip.children[1].children],
                         ["Kajoj", "Karolczi", "Krell", "Maszrumisko", "Szczepan", "Waluś", "Żaba Boży"])

    def test_tagged_text_renders_focusable_tooltip_and_keeps_plain_text(self):
        rendered = tags.render_tagged_text("Lists: [[tag:army_lists:rohan]]!")
        self.assertIsInstance(rendered, html.Span)
        self.assertEqual(rendered.children[0], "Lists: ")
        keyword = rendered.children[1].children
        tooltip = rendered.children[1].label
        self.assertEqual(rendered.children[1].classNames["tooltip"], "tag-tooltip-popup")
        self.assertNotIn("className", rendered.children[1].to_plotly_json()["props"])
        self.assertEqual(keyword.className, "tag-keyword")
        self.assertEqual(keyword.tabIndex, 0)
        self.assertEqual(tooltip.children[0].children, "Rohan")
        self.assertEqual(
            [line.children for line in tooltip.children[1].children],
            ["Army of Edoras", "Defenders of Helm's Deep", "Defenders of the Hornburg",
             "Fields of Celebrant", "Fords of Isen", "Kingdom of Rohan", "Paths of the Drúadan",
             "Ride Out", "Riders of Eomer", "Riders of Theoden", "Road to Helm's Deep",
             "The Grief of Éomer"],
        )
        self.assertEqual(rendered.children[2], "!")

    def test_return_of_the_king_appears_only_in_good_men_description(self):
        self.assertNotIn("Return of the King", tags.get_tag("army_lists", "rohan").desc.splitlines())
        self.assertIn("Return of the King", tags.get_tag("army_lists", "good-men").desc.splitlines())

    def test_radagasts_alliance_is_in_monsters_tag_and_tooltip(self):
        self.assertTrue(tags.has_tag("army_lists", "monsters", 343))
        tooltip = tags.render_tagged_text("[[tag:army_lists:monsters]]").children[0].label
        self.assertIn("Radagast's Alliance", [line.children for line in tooltip.children[1].children])

    def test_silesia_tooltip_lists_each_tagged_city(self):
        rendered = tags.render_tagged_text("[[tag:places:silesia]]")
        tooltip = rendered.children[0].label
        self.assertEqual(
            [line.children for line in tooltip.children[1].children],
            ["Chorzów", "Gliwice", "Jastrzębie-Zdrój", "Katowice", "Pszczyna",
             "Rybnik", "Sosnowiec", "Tychy", "Zabrze", "Zawadzkie"],
        )

    def test_abroad_tag_contains_foreign_cities_and_sosnowiec(self):
        tag = tags.get_tag("places", "abroad")
        self.assertEqual(set(tag.items), {2692, 2733, 2180, 3147, 643})
        tooltip = tags.render_tagged_text("[[tag:places:abroad]]").children[0].label
        self.assertEqual(tooltip.children[0].children, "Abroad")
        self.assertEqual(
            [line.children for line in tooltip.children[1].children],
            ["Kharkiv", "New York", "San Juan", "Sosnowiec", "Toronto"],
        )

    def test_tricity_tag_contains_available_places(self):
        tag = tags.get_tag("places", "tricity")
        self.assertEqual(set(tag.items), {234, 3117, 3118})
        tooltip = tags.render_tagged_text("[[tag:places:tricity]]").children[0].label
        self.assertEqual(tooltip.children[0].children, "Trójmiasto")
        self.assertEqual(
            [line.children for line in tooltip.children[1].children],
            ["Gdańsk", "Gdynia", "Trójmiasto"],
        )

    def test_article_markdown_supports_tag_references(self):
        body, _ = render_body("Rohan lists: [[tag:army_lists:rohan]].")
        self.assertEqual(len(body), 1)
        self.assertIsInstance(body[0], html.Span)
        self.assertEqual(body[0].children[0].children, "Rohan lists:")
        self.assertEqual(body[0].children[1], " ")
        self.assertEqual(body[0].children[2].children.children, "Rohan")
        self.assertEqual(body[0].children[3].children, ".")

    def test_plain_markdown_remains_dash_markdown(self):
        body, _ = render_body("**No tag here.**")
        self.assertEqual(body[0].className, "article-body")


if __name__ == "__main__":
    unittest.main()
