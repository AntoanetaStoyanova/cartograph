from cartograph.config import LANGUAGES


def test_languages_are_non_empty_and_unique() -> None:
    assert LANGUAGES
    assert len(set(LANGUAGES)) == len(LANGUAGES)
