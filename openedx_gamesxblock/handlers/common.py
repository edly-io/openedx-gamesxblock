"""
Shared authoring handlers: studio_view rendering, save_settings, and
upload_image. These are the same regardless of which game_type is selected --
studio_view itself switches which content section is visible based on the
currently saved game_type, and save_settings validates+stores only the
fields relevant to whichever game_type is being saved.
"""

import hashlib
import json
import uuid

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from web_fragments.fragment import Fragment
from webob import Response
from xblock.utils.resources import ResourceLoader

from ..constants import CardField, ClozeField, Default, GameType, Limits, MemoryField, SequenceField

resource_loader = ResourceLoader("openedx_gamesxblock")

_ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "svg"}


class CommonHandlers:
    """Authoring (studio_view) handlers shared across all game types."""

    @staticmethod
    def studio_view(xblock, context=None):  # pylint: disable=unused-argument
        """Render the single editor covering every game type; JS shows/hides sections by game_type."""
        # Sent as one JSON blob (read by studio.js) rather than walked row-by-row
        # by the Django template, since each game's rows need custom per-field
        # JS behavior (image upload buttons, move up/down, comma-split lists)
        # that's easier to drive from one client-side seeding function.
        initial_data = {
            "cards": list(xblock.cards),
            "sequence_items": list(xblock.sequence_items),
            "cloze_blanks": list(xblock.cloze_blanks),
            # Normalized to {"word": ...} dicts so every repeatable section's
            # initial rows share the same "list of field-dicts" shape client-side.
            "wordsearch_words": [{"word": word} for word in xblock.wordsearch_words],
            "memory_pairs": list(xblock.memory_pairs),
        }

        # Server-generated JSON (never user input), safe to mark as such for direct embedding.
        initial_data_json = mark_safe(json.dumps(initial_data))  # noqa: S308

        html = resource_loader.render_django_template(
            "/static/html/studio.html",
            {
                "display_name": xblock.display_name,
                "game_type": xblock.game_type,
                "instructions": xblock.instructions,
                "is_shuffled": xblock.is_shuffled,
                "weight": xblock.weight,
                "max_attempts": xblock.max_attempts,
                "timer_enabled": xblock.timer_enabled,
                "cloze_text": xblock.cloze_text,
                "initial_data_json": initial_data_json,
                "game_types": GameType.ALL,
                "graded_game_types": GameType.GRADED,
            },
        )

        frag = Fragment(html)
        frag.add_css(resource_loader.load_unicode("/static/css/studio.css"))
        frag.add_javascript(resource_loader.load_unicode("/static/js/src/studio.js"))
        frag.initialize_js("GamesXBlockStudio")
        return frag

    @staticmethod
    def _validate_cards(raw_cards):
        """Validate+normalize matching cards, assigning a stable card_id where missing."""
        cards = []
        for raw in raw_cards[:Limits.MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            term = str(raw.get(CardField.TERM, "")).strip()[:Limits.MAX_TEXT_LENGTH]
            definition = str(raw.get(CardField.DEFINITION, "")).strip()[:Limits.MAX_TEXT_LENGTH]
            if not term or not definition:
                continue
            cards.append({
                CardField.CARD_ID: raw.get(CardField.CARD_ID) or str(uuid.uuid4()),
                CardField.TERM: term,
                CardField.TERM_IMAGE: str(raw.get(CardField.TERM_IMAGE, "") or ""),
                CardField.DEFINITION: definition,
                CardField.DEFINITION_IMAGE: str(raw.get(CardField.DEFINITION_IMAGE, "") or ""),
            })
        return cards

    @staticmethod
    def _validate_sequence_items(raw_items):
        """Validate+normalize sequencing items; correct order is simply their authored list order."""
        items = []
        for raw in raw_items[:Limits.MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get(SequenceField.TEXT, "")).strip()[:Limits.MAX_TEXT_LENGTH]
            if not text:
                continue
            items.append({
                SequenceField.ITEM_ID: raw.get(SequenceField.ITEM_ID) or str(uuid.uuid4()),
                SequenceField.TEXT: text,
            })
        return items

    @staticmethod
    def _validate_cloze_blanks(raw_blanks):
        """Validate+normalize cloze blanks."""
        blanks = []
        for raw in raw_blanks[:Limits.MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            token = str(raw.get(ClozeField.TOKEN, "")).strip()
            answers = [
                str(a).strip()[:Limits.MAX_TEXT_LENGTH]
                for a in (raw.get(ClozeField.ANSWERS) or [])
                if str(a).strip()
            ]
            if not token or not answers:
                continue
            distractors = [
                str(d).strip()[:Limits.MAX_TEXT_LENGTH]
                for d in (raw.get(ClozeField.DISTRACTORS) or [])
                if str(d).strip()
            ]
            blanks.append({ClozeField.TOKEN: token, ClozeField.ANSWERS: answers, ClozeField.DISTRACTORS: distractors})
        return blanks

    @staticmethod
    def _validate_wordsearch_words(raw_words):
        """Validate+normalize word-search words."""
        words = []
        for raw in raw_words[:Limits.MAX_ITEMS]:
            word = str(raw).strip()
            if len(word) >= Limits.MIN_WORD_SEARCH_WORD_LENGTH and word.isalpha():
                words.append(word.upper())
        return words

    @staticmethod
    def _validate_memory_pairs(raw_pairs):
        """Validate+normalize memory-game pairs."""
        pairs = []
        for raw in raw_pairs[:Limits.MAX_ITEMS]:
            if not isinstance(raw, dict):
                continue
            side_a = str(raw.get(MemoryField.A, "")).strip()[:Limits.MAX_TEXT_LENGTH]
            side_b = str(raw.get(MemoryField.B, "")).strip()[:Limits.MAX_TEXT_LENGTH]
            if not side_a or not side_b:
                continue
            pairs.append({
                MemoryField.PAIR_ID: raw.get(MemoryField.PAIR_ID) or str(uuid.uuid4()),
                MemoryField.A: side_a,
                MemoryField.B: side_b,
            })
        return pairs

    @staticmethod
    def save_settings(xblock, data, suffix=""):  # pylint: disable=unused-argument
        """
        Persist authored settings and whichever content list matches the
        submitted game_type. Fields for other game types are left untouched,
        so switching game_type and back doesn't lose previously authored content.
        """
        game_type = data.get("game_type", Default.GAME_TYPE)
        if game_type not in GameType.ALL:
            return {"success": False, "error": _("Unknown game type.")}

        xblock.display_name = str(data.get("display_name", xblock.display_name) or Default.DISPLAY_NAME)
        xblock.instructions = str(data.get("instructions", "") or "")
        xblock.is_shuffled = bool(data.get("is_shuffled", Default.IS_SHUFFLED))
        xblock.timer_enabled = bool(data.get("timer_enabled", Default.TIMER_ENABLED))
        xblock.game_type = game_type

        if game_type in GameType.GRADED:
            try:
                xblock.weight = max(0.0, float(data.get("weight", Default.WEIGHT)))
            except (TypeError, ValueError):
                xblock.weight = Default.WEIGHT
            try:
                xblock.max_attempts = max(0, int(data.get("max_attempts", Default.MAX_ATTEMPTS)))
            except (TypeError, ValueError):
                xblock.max_attempts = Default.MAX_ATTEMPTS

        if game_type == GameType.MATCHING:
            xblock.cards = CommonHandlers._validate_cards(data.get("cards") or [])
        elif game_type == GameType.SEQUENCING:
            xblock.sequence_items = CommonHandlers._validate_sequence_items(data.get("sequence_items") or [])
        elif game_type == GameType.CLOZE:
            xblock.cloze_text = str(data.get("cloze_text", "") or "")[:Limits.MAX_TEXT_LENGTH * 10]
            xblock.cloze_blanks = CommonHandlers._validate_cloze_blanks(data.get("cloze_blanks") or [])
        elif game_type == GameType.WORD_SEARCH:
            xblock.wordsearch_words = CommonHandlers._validate_wordsearch_words(data.get("wordsearch_words") or [])
        elif game_type == GameType.MEMORY:
            xblock.memory_pairs = CommonHandlers._validate_memory_pairs(data.get("memory_pairs") or [])

        return {"success": True, "game_type": xblock.game_type}

    @staticmethod
    def upload_image(xblock, request, suffix=""):  # pylint: disable=unused-argument
        """
        Upload an image (used by matching-card fields) to Django's default
        storage and return its URL. Deduplicates by content hash so
        re-uploading the same image doesn't create redundant files.
        """
        try:
            upload = request.params["file"]
            file_name = upload.filename or ""
            if "." not in file_name:
                return Response(json_body={"success": False, "error": _("File must have an extension")}, status=400)

            ext = file_name.rsplit(".", 1)[1].lower()
            if ext not in _ALLOWED_IMAGE_EXTENSIONS:
                return Response(
                    json_body={
                        "success": False,
                        "error": _("Unsupported file type '.{ext}'. Allowed: {allowed}").format(
                            ext=ext, allowed=", ".join(sorted(_ALLOWED_IMAGE_EXTENSIONS))
                        ),
                    },
                    status=400,
                )

            blob = upload.file.read()
            file_hash = hashlib.sha256(blob).hexdigest()[:32]
            block_id = xblock.scope_ids.usage_id.block_id
            file_path = f"openedx_gamesxblock/{block_id}/{file_hash}.{ext}"

            if not default_storage.exists(file_path):
                default_storage.save(file_path, ContentFile(blob))

            return Response(json_body={"success": True, "url": default_storage.url(file_path)})
        except Exception as exc:  # pylint: disable=broad-except
            return Response(json_body={"success": False, "error": str(exc)}, status=400)
