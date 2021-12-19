import pytest
import pyautogui
import goban_irl.helpers as helpers
import goban_irl.opencv_utilities as utils

from goban_irl.board import Board
from unittest.mock import patch
from hypothesis import given, strategies as st


class MockImage:
    def __init__(self, height=200, width=200):
        self.height = height
        self.width = width
        self.shape = (self.height, self.width, False)


@given(initial_string=st.text())
def test_boxify(initial_string):
    result = helpers.boxify(initial_string)
    assert len(result) == 3 * (len(initial_string) + 6) + 4


@given(
    bad_answers=st.lists(
        st.text().filter(
            lambda x: x not in ["y", "Y", "yes", "Yes", ""]
            and x not in ["n", "N", "no", "No"]
        )
    )
)
def test_prompt_handler(bad_answers):
    yes_answers = ["y", "Y", "yes", "Yes", ""]
    no_answers = ["n", "N", "no", "No"]
    for user_input in yes_answers:
        with patch("builtins.input", return_value=user_input):
            assert helpers.prompt_handler("Would you like to continue")

    for user_input in no_answers:
        with patch("builtins.input", return_value=user_input):
            assert not helpers.prompt_handler("Would you like to continue")

    with patch("builtins.input", side_effect=bad_answers + ["n"]):
        assert not helpers.prompt_handler("Would you like to continue")


@given(
    screenshot_height=st.integers(min_value=1),
    pyautogui_screenshot_height=st.integers(min_value=1),
)
def test_get_scale(screenshot_height, pyautogui_screenshot_height):
    with patch(
        "goban_irl.opencv_utilities.get_snapshot",
        return_value=MockImage(height=screenshot_height),
    ), patch(
        "pyautogui.size", return_value=MockImage(height=pyautogui_screenshot_height)
    ):
        assert helpers.get_scale() == screenshot_height / pyautogui_screenshot_height
        assert utils.get_snapshot.called
        assert pyautogui.size.called


@given(
    click_location=st.tuples(
        st.integers(min_value=0, max_value=100000),
        st.integers(min_value=0, max_value=100000),
    )
)
def test_get_nearest_intersection(click_location):
    assert (click_location[1], click_location[0]) == helpers.get_nearest_intersection(
        1, 1, click_location
    )
    assert (
        round(click_location[1] / 3),
        round(click_location[0] / 5),
    ) == helpers.get_nearest_intersection(5, 3, click_location)


def test_click():
    """Stub pyautogui position, moveTo, and click
    Check the click location on a virtual board
    """

    corners = [(888, 248), (2470, 1830)]
    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)

    for i in range(19):
        with patch("pyautogui.position", return_value=(0, 0)), patch(
            "pyautogui.moveTo"
        ), patch("pyautogui.click"):
            helpers.click(board, (i, 0, "empty", "black"), screen_scale=1)
            helpers.click(board, (0, i, "empty", "black"), screen_scale=1)

            assert pyautogui.position.called
            assert pyautogui.moveTo.call_args_list[0].args[0] == corners[0][0]
            assert pyautogui.moveTo.call_args_list[1].args == (0, 0)
            assert pyautogui.moveTo.call_args_list[2].args[1] == corners[0][1]
            assert pyautogui.moveTo.call_args_list[3].args == (0, 0)
            assert pyautogui.click.called


def test_print_describe_missing(capsys):
    missing_stones = [
        (0, 0, "black", "empty"),
        (1, 1, "empty", "white"),
        (2, 2, "black", "white"),
    ]

    helpers.print_describe_missing(missing_stones, "myboard")
    helpers.print_describe_missing([], "myboard_2")
    helpers.print_describe_missing(2 * missing_stones, "myboard_3")
    captured = capsys.readouterr().out

    assert "A19" in captured
    assert "B18" in captured
    assert "C17" in captured

    assert "1-19" in captured
    assert "2-18" in captured
    assert "3-17" in captured

    assert "myboard has black and other board has empty" in captured
    assert "myboard has empty and other board has white" in captured
    assert "myboard has black and other board has white" in captured

    assert "Board myboard_2 is not missing any stones" in captured
    assert "Board myboard_3 is missing many stones (6)" in captured
