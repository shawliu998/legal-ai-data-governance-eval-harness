from legal_eval_harness.utils import extract_first_json_object, parse_bool


def test_extract_first_json_object_from_wrapped_text():
    parsed = extract_first_json_object('prefix {"a": 1, "b": {"c": 2}} suffix')
    assert parsed == {"a": 1, "b": {"c": 2}}


def test_parse_bool_handles_csv_string_round_trips():
    assert parse_bool("True") is True
    assert parse_bool("yes") is True
    assert parse_bool("是") is True
    assert parse_bool("False") is False
    assert parse_bool("no") is False
    assert parse_bool("") is False
