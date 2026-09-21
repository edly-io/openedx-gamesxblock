"""
Tests for shared authoring handlers: save_settings and upload_image.
"""

import io
import json
import tempfile

from django.test import SimpleTestCase, override_settings

from openedx_gamesxblock.constants import CardField, GameType

from .test_utils import make_block


class _FakeRequest:
    method = "POST"

    def __init__(self, payload):
        self.body = json.dumps(payload).encode("utf-8")


class _FakeUpload:
    """Stand-in for the webob multipart file-upload param object."""

    def __init__(self, filename, content):
        self.filename = filename
        self.file = io.BytesIO(content)


class _FakeUploadRequest:
    """Stand-in for the webob Request passed to the (non-JSON) `upload_image` handler."""

    def __init__(self, filename, content):
        self.params = {"file": _FakeUpload(filename, content)}


class SaveSettingsTests(SimpleTestCase):
    """Verify save_settings validates and persists content per game_type."""

    def test_save_matching_cards(self):
        block = make_block()
        response = json.loads(block.save_settings(_FakeRequest({
            "game_type": "matching",
            "cards": [{"term": "A", "definition": "one"}, {"term": "B", "definition": "two"}],
        })).body)
        self.assertTrue(response["success"])
        self.assertEqual(block.game_type, GameType.MATCHING)
        self.assertEqual(len(block.cards), 2)
        self.assertTrue(block.cards[0][CardField.CARD_ID])  # a card_id was assigned

    def test_incomplete_card_rows_are_dropped(self):
        block = make_block()
        block.save_settings(_FakeRequest({
            "game_type": "matching",
            "cards": [
                {"term": "A", "definition": ""},
                {"term": "", "definition": "two"},
                {"term": "C", "definition": "three"},
            ],
        }))
        self.assertEqual(len(block.cards), 1)
        self.assertEqual(block.cards[0]["term"], "C")

    def test_switching_game_type_preserves_other_game_types_content(self):
        block = make_block()
        block.save_settings(_FakeRequest({"game_type": "matching", "cards": [{"term": "A", "definition": "one"}]}))
        block.save_settings(_FakeRequest({"game_type": "sequencing", "sequence_items": [{"text": "Step"}]}))
        # Switching to sequencing must not have wiped the previously authored matching cards.
        self.assertEqual(len(block.cards), 1)
        self.assertEqual(block.game_type, GameType.SEQUENCING)

    def test_unknown_game_type_rejected(self):
        block = make_block()
        response = json.loads(block.save_settings(_FakeRequest({"game_type": "not-a-real-game"})).body)
        self.assertFalse(response["success"])

    def test_weight_and_max_attempts_only_saved_for_graded_types(self):
        block = make_block(weight=1.0, max_attempts=3)
        block.save_settings(_FakeRequest({"game_type": "word_search", "weight": 99, "max_attempts": 99}))
        # word_search is ungraded -- grading fields must be left at their prior values, not overwritten.
        self.assertEqual(block.weight, 1.0)
        self.assertEqual(block.max_attempts, 3)

    def test_invalid_weight_falls_back_to_default(self):
        block = make_block()
        block.save_settings(_FakeRequest({"game_type": "matching", "weight": "not-a-number"}))
        self.assertEqual(block.weight, 1.0)

    def test_wordsearch_words_normalized_uppercase_and_filtered(self):
        block = make_block()
        block.save_settings(_FakeRequest({"game_type": "word_search", "wordsearch_words": ["cat", "a", "123", "dog"]}))
        # "a" is below the minimum length and "123" isn't alphabetic -- both dropped.
        self.assertEqual(block.wordsearch_words, ["CAT", "DOG"])

    def test_incomplete_sequence_rows_are_dropped(self):
        block = make_block()
        block.save_settings(_FakeRequest({
            "game_type": "sequencing",
            "sequence_items": [{"text": "Step one"}, {"text": ""}, {"text": "  "}],
        }))
        self.assertEqual(len(block.sequence_items), 1)

    def test_incomplete_memory_rows_are_dropped(self):
        block = make_block()
        block.save_settings(_FakeRequest({
            "game_type": "memory",
            "memory_pairs": [{"a": "Cat", "b": "Meow"}, {"a": "Dog", "b": ""}, {"a": "", "b": "Quack"}],
        }))
        self.assertEqual(len(block.memory_pairs), 1)
        self.assertEqual(block.memory_pairs[0]["a"], "Cat")

    def test_non_dict_rows_are_ignored_rather_than_crashing(self):
        block = make_block()
        response = json.loads(block.save_settings(_FakeRequest({
            "game_type": "matching",
            "cards": ["not-a-dict", 42, None, {"term": "A", "definition": "one"}],
        })).body)
        self.assertTrue(response["success"])
        self.assertEqual(len(block.cards), 1)

    def test_cloze_blanks_require_token_and_at_least_one_answer(self):
        block = make_block()
        block.save_settings(_FakeRequest({
            "game_type": "cloze",
            "cloze_blanks": [
                {"token": "c1", "answers": ["Paris"]},
                {"token": "", "answers": ["dropped"]},
                {"token": "c2", "answers": []},
            ],
        }))
        self.assertEqual(len(block.cloze_blanks), 1)
        self.assertEqual(block.cloze_blanks[0]["token"], "c1")


class UploadImageTests(SimpleTestCase):
    """Verify upload_image validates extensions and returns a usable URL."""

    def test_rejects_disallowed_extension(self):
        block = make_block()
        response = block.upload_image(_FakeUploadRequest("payload.exe", b"data"))
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", json.loads(response.body)["error"])

    def test_rejects_filename_without_extension(self):
        block = make_block()
        response = block.upload_image(_FakeUploadRequest("noextension", b"data"))
        self.assertEqual(response.status_code, 400)

    def test_accepts_allowed_extension_and_returns_a_url(self):
        with tempfile.TemporaryDirectory() as tmp_media_root:
            with override_settings(MEDIA_ROOT=tmp_media_root, MEDIA_URL="/media/"):
                block = make_block()
                response = json.loads(block.upload_image(_FakeUploadRequest("photo.png", b"fake-png-bytes")).body)
                self.assertTrue(response["success"])
                self.assertTrue(response["url"].endswith(".png"))

    def test_reuploading_identical_bytes_deduplicates_by_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp_media_root:
            with override_settings(MEDIA_ROOT=tmp_media_root, MEDIA_URL="/media/"):
                block = make_block()
                first = json.loads(block.upload_image(_FakeUploadRequest("a.png", b"same-bytes")).body)
                second = json.loads(block.upload_image(_FakeUploadRequest("b.png", b"same-bytes")).body)
                # Same content -> same hash -> same stored file/url, even though filenames differ.
                self.assertEqual(first["url"], second["url"])
