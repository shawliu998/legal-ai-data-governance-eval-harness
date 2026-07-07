from legal_eval_harness.utils import extract_first_json_object


def test_extract_first_json_object_from_wrapped_text():
    parsed = extract_first_json_object('prefix {"a": 1, "b": {"c": 2}} suffix')
    assert parsed == {"a": 1, "b": {"c": 2}}

