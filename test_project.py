import base64
import random

import pytest

import project


def test_get_base64_encoded_credentials():
    result = project.get_base64_encoded_credentials("client", "secret")
    assert base64.b64decode(result).decode() == "client:secret"


def test_shuffled_copy_is_deterministic_and_does_not_mutate_input():
    original = ["a", "b", "c", "d"]
    result = project.shuffled_copy(original, random.Random(7))
    assert result == ["d", "b", "a", "c"]
    assert original == ["a", "b", "c", "d"]


def test_chunked_uses_spotify_batch_size():
    values = [str(number) for number in range(205)]
    assert [len(batch) for batch in project.chunked(values)] == [100, 100, 5]


def test_chunked_rejects_invalid_size():
    with pytest.raises(ValueError):
        project.chunked(["a"], 0)


def test_fetch_all_pages():
    class FakeSpotify:
        def next(self, page):
            return {"items": [3], "next": None}

    first_page = {"items": [1, 2], "next": "next-page"}
    assert project.fetch_all_pages(FakeSpotify(), first_page) == [1, 2, 3]


def test_print_app_name():
    assert project.print_app_name() == "Welcome to SpotifyTools!"
