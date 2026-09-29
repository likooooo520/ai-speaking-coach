import json
import unittest
from pathlib import Path
from unittest.mock import patch

from app.expression_library import ExpressionLibrary


class ExpressionLibraryTests(unittest.TestCase):
    def test_loads_seeded_library_with_required_fields(self):
        library = ExpressionLibrary()
        self.assertGreaterEqual(len(library.entries), 20)
        required = {"expression", "meaning", "level", "category", "situations", "alternatives", "examples", "naturalness_notes", "formality", "tags"}
        self.assertTrue(required.issubset(library.entries[0]))

    def test_invalid_json_and_missing_fields_are_safe(self):
        path = Path("library-test.json")
        with patch.object(Path, "read_text", return_value="not json"):
            self.assertEqual(ExpressionLibrary(path).entries, [])
        with patch.object(Path, "read_text", return_value=json.dumps([{"id": "missing"}])):
            self.assertEqual(ExpressionLibrary(path).entries, [])

    def test_structured_filters_and_keyword_search(self):
        library = ExpressionLibrary()
        self.assertTrue(library.search(category="preference"))
        self.assertTrue(library.search(situation="talking_about_food"))
        self.assertTrue(library.search(level="B1"))
        self.assertTrue(library.search(query="sparkling water"))
        self.assertEqual(library.search(query="quantum teleportation"), [])

    def test_relevance_uses_food_and_preference_signal(self):
        library = ExpressionLibrary()
        results = library.find_relevant("I like sparkling water very much.", "food", "B2")
        self.assertEqual(len(results), 1)
        self.assertIn(results[0]["expression"], {"I'm really into...", "I'm a big fan of..."})

    def test_hobby_relevance_is_available_without_forcing_unknown_topics(self):
        library = ExpressionLibrary()
        self.assertTrue(library.find_relevant("I really like cooking.", "hobbies", "B2"))
        self.assertEqual(library.find_relevant("I need to discuss quantum teleportation.", "science", "B2"), [])


if __name__ == "__main__":
    unittest.main()
