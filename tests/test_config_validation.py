"""Tests for the rules that keep a live config edit from breaking the bot at runtime."""

import pytest

from ticketbot.models import MAX_SELECT_FIELD_LENGTH, MAX_TICKET_TYPES
from ticketbot.utils.config_validation import (
    SETTABLE,
    SETTING_SPECS,
    SPECS_BY_KEY,
    ConfigValidationError,
    coerce_setting,
    format_setting_value,
    parse_bool,
    parse_color,
    parse_message_id,
    parse_status_type,
    setting_label,
    validate_room_for_new_type,
    validate_type_fields,
)


class TestParseBool:
    @pytest.mark.parametrize("raw", ["true", "True", "YES", "on", "1", "enable", "enabled"])
    def test_accepts_truthy_words(self, raw):
        assert parse_bool(raw) is True

    @pytest.mark.parametrize("raw", ["false", "False", "NO", "off", "0", "disable", "disabled"])
    def test_accepts_falsey_words(self, raw):
        assert parse_bool(raw) is False

    def test_rejects_anything_else(self):
        with pytest.raises(ConfigValidationError, match="not a yes/no value"):
            parse_bool("maybe")


class TestParseColor:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("0xFFFFFF", 0xFFFFFF),
            ("#5865F2", 0x5865F2),
            ("5865F2", 0x5865F2),
            ("0x000000", 0x000000),
            ("ffffff", 0xFFFFFF),
            ("  #5865F2  ", 0x5865F2),
            ("123456", 0x123456),
        ],
    )
    def test_accepts_hex_forms(self, raw, expected):
        assert parse_color(raw) == expected

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("#58F", 0x5588FF), ("fff", 0xFFFFFF), ("0x000", 0x000000)],
    )
    def test_expands_three_digit_shorthand(self, raw, expected):
        assert parse_color(raw) == expected

    def test_digits_are_never_read_as_decimal(self):
        assert parse_color("255") != 255

    @pytest.mark.parametrize("raw", ["0x1000000", "5865F", "ffffffff", "12345"])
    def test_rejects_wrong_digit_count(self, raw):
        with pytest.raises(ConfigValidationError, match="a color code needs 6"):
            parse_color(raw)

    @pytest.mark.parametrize(
        "raw",
        [
            "blurple",
            "",
            "#GGGGGG",
            "5865_F2",
            "-5865F2",
            "##5865F2",
            "#0x5865F2",
            "rgb(88,101,242)",
        ],
    )
    def test_rejects_non_hex(self, raw):
        with pytest.raises(ConfigValidationError, match="not a hex color code"):
            parse_color(raw)


class TestParseStatusType:
    def test_normalizes_casing(self):
        assert parse_status_type("watching") == "Watching"

    def test_rejects_unknown_type(self):
        with pytest.raises(ConfigValidationError, match="not a status type"):
            parse_status_type("Vibing")


class TestCoerceSetting:
    def test_routes_each_setting_to_its_parser(self):
        assert coerce_setting("embed_color", "#5865F2") == 0x5865F2
        assert coerce_setting("multiple_tickets_allowed", "yes") is True
        assert coerce_setting("bot_status_type", "listening") == "Listening"
        assert coerce_setting("footer_of_embeds", "My Server") == "My Server"

    def test_rejects_settings_that_are_not_live_editable(self):
        # bot_token and database_url stay in .env; they must not be settable over Discord.
        with pytest.raises(ConfigValidationError, match="not a live-editable setting"):
            coerce_setting("bot_token", "hunter2")


class TestValidateTypeFields:
    def test_accepts_a_normal_type(self):
        validate_type_fields("sales", "Sales 💲", "Create a sales related ticket.")

    @pytest.mark.parametrize("field", ["key", "label", "description"])
    def test_rejects_empty_fields(self, field):
        fields = {"key": "sales", "label": "Sales", "description": "Talk to sales."}
        fields[field] = "   "
        with pytest.raises(ConfigValidationError, match="cannot be empty"):
            validate_type_fields(**fields)

    def test_rejects_padded_keys(self):
        with pytest.raises(ConfigValidationError, match="whitespace"):
            validate_type_fields("sales ", "Sales", "Talk to sales.")

    def test_rejects_fields_over_discords_limit(self):
        too_long = "x" * (MAX_SELECT_FIELD_LENGTH + 1)
        with pytest.raises(ConfigValidationError, match=str(MAX_SELECT_FIELD_LENGTH)):
            validate_type_fields("sales", too_long, "Talk to sales.")

    def test_accepts_fields_exactly_at_the_limit(self):
        validate_type_fields("sales", "x" * MAX_SELECT_FIELD_LENGTH, "ok")


class TestValidateRoomForNewType:
    def test_accepts_when_there_is_room(self):
        validate_room_for_new_type(("sales", "support"), "staff")

    def test_rejects_duplicate_keys(self):
        with pytest.raises(ConfigValidationError, match="already exists"):
            validate_room_for_new_type(("sales",), "sales")

    def test_rejects_the_twenty_sixth_type(self):
        # Discord select menus hold 25 options; a 26th would make the creation dropdown
        # fail to render at all.
        existing = tuple(f"type{index}" for index in range(MAX_TICKET_TYPES))
        with pytest.raises(ConfigValidationError, match=str(MAX_TICKET_TYPES)):
            validate_room_for_new_type(existing, "one-too-many")

    def test_accepts_the_twenty_fifth_type(self):
        existing = tuple(f"type{index}" for index in range(MAX_TICKET_TYPES - 1))
        validate_room_for_new_type(existing, "last-one")


class TestSettingSpecs:
    """The display layer that lets slash commands show `Embed Color` for `embed_color`."""

    def test_settable_is_derived_from_the_specs(self):
        assert SETTABLE == {spec.key: spec.kind for spec in SETTING_SPECS}

    def test_every_setting_has_a_human_label(self):
        for spec in SETTING_SPECS:
            assert spec.label != spec.key
            assert "_" not in spec.label

    def test_labels_are_unique(self):
        labels = [spec.label for spec in SETTING_SPECS]
        assert len(set(labels)) == len(labels)

    def test_every_example_survives_its_own_coercion(self):
        for spec in SETTING_SPECS:
            coerce_setting(spec.key, spec.example)

    def test_specs_by_key_covers_every_spec(self):
        assert set(SPECS_BY_KEY) == {spec.key for spec in SETTING_SPECS}

    def test_setting_label_falls_back_to_the_raw_key(self):
        assert setting_label("embed_color") == "Embed Color"
        assert setting_label("not_a_setting") == "not_a_setting"


class TestFormatSettingValue:
    def test_renders_colors_as_hex(self):
        assert format_setting_value("embed_color", 0x5865F2) == "#5865F2"

    def test_pads_short_colors(self):
        assert format_setting_value("embed_color", 0xFF) == "#0000FF"

    @pytest.mark.parametrize(
        ("value", "expected"), [(True, "Enabled"), (False, "Disabled")]
    )
    def test_renders_bools_as_words(self, value, expected):
        assert format_setting_value("dm_ticket_copies", value) == expected

    @pytest.mark.parametrize("value", [None, ""])
    def test_marks_missing_values(self, value):
        assert format_setting_value("footer_of_embeds", value) == "*not set*"

    def test_passes_strings_through(self):
        assert format_setting_value("footer_of_embeds", "My Server") == "My Server"

    def test_round_trips_a_parsed_color(self):
        assert format_setting_value("embed_color", parse_color("#5865F2")) == "#5865F2"


class TestParseMessageId:
    def test_accepts_a_bare_id(self):
        assert parse_message_id("1402318374923746816") == 1402318374923746816

    def test_strips_surrounding_whitespace(self):
        assert parse_message_id("  1402318374923746816  ") == 1402318374923746816

    def test_accepts_a_message_link(self):
        link = "https://discord.com/channels/123/456/1402318374923746816"
        assert parse_message_id(link) == 1402318374923746816

    def test_accepts_a_canary_link(self):
        link = "https://canary.discord.com/channels/123/456/1402318374923746816/"
        assert parse_message_id(link) == 1402318374923746816

    def test_accepts_the_channel_dash_message_form(self):
        assert parse_message_id("456-1402318374923746816") == 1402318374923746816

    @pytest.mark.parametrize("raw", ["", "not-an-id", "14023183749237468xx", "12.5", "<@123>"])
    def test_rejects_non_numeric(self, raw):
        with pytest.raises(ConfigValidationError, match="is not a message ID"):
            parse_message_id(raw)

    @pytest.mark.parametrize("raw", ["123", "1234567890123456789012345"])
    def test_rejects_implausible_lengths(self, raw):
        with pytest.raises(ConfigValidationError, match="digits"):
            parse_message_id(raw)

    def test_never_returns_a_negative_id(self):
        with pytest.raises(ConfigValidationError, match="is not a message ID"):
            parse_message_id("-1402318374923746816")
