import pytest
import goban_irl.ui as ui
import goban_irl.opencv_utilities as utils

from goban_irl.board import Board
from unittest.mock import patch


def test_print_functions(capsys):
    """Check the beginning and end of each printed message"""
    ui.welcome_message()
    ui.cornerloader_text()
    ui.calibrate_text()
    captured = capsys.readouterr().out

    assert "Welcome!" in captured
    assert "multiple boards" in captured
    assert "Select two or four" in captured
    assert "Enter to continue" in captured
    assert "Place white and black" in captured
    assert "in that order." in captured


def test_show_boards_list(capsys):
    load_options = ui.show_boards_list()
    captured = capsys.readouterr().out
    assert "Existing boards:" in captured
    assert "sample.json" in captured
    assert "sample.json" in load_options


def test_load_existing_metadata(capsys):
    board_metadata, board_exists = ui.load_existing_metadata({"path": "sample.json"})
    assert board_exists
    captured = capsys.readouterr().out
    sample_board_properties = {
        "name": "sample",
        "path": "sample.json",
        "delay": 0,
        "loader_type": "virtual",
        "flip": False,
        "click": True,
        "corners": [[888, 248], [2470, 1830]],
        "detection_function": "check_max_difference",
        "cutoffs": [650, 750],
    }
    for key, value in sample_board_properties.items():
        assert "{} = {}\n".format(key, value) in captured

    _, board_exists = ui.load_existing_metadata({"path": "not_exist.json"})
    assert not board_exists


def test_interactive_corners(capsys):
    corners = [(0, 0), (1, 1)]
    with patch("goban_irl.opencv_utilities.get_snapshot"), patch(
        "goban_irl.opencv_utilities.get_clicks", return_value=corners
    ), patch("builtins.input", return_value=""):
        result = ui.interactive_corners("virtual")
        captured = capsys.readouterr().out
        assert "Select two or four" in captured
        for corner in corners:
            assert corner in result


def test_interactive_calibrate(capsys):
    corners = [(888, 248), (2470, 1830)]
    image_path = "tests/image_samples/find_stones_test_1.png"
    board = Board(image=image_path, corners=corners)
    black_stones = [board.intersections[i][j] for (i, j) in [(18, 18), (3, 15)]]
    white_stones = [board.intersections[i][j] for (i, j) in [(0, 0), (15, 3)]]
    empty_spaces = [
        board.intersections[i][j] for (i, j) in [(1, 1), (17, 17), (1, 17), (17, 1)]
    ]

    with patch(
        "goban_irl.opencv_utilities.get_snapshot",
        return_value=utils.import_image(image_path),
    ), patch(
        "goban_irl.opencv_utilities.get_clicks",
        side_effect=[black_stones, white_stones, empty_spaces],
    ), patch(
        "builtins.input", return_value=""
    ):
        detection_function, cutoffs = ui.interactive_calibrate(corners, "virtual")
        captured = capsys.readouterr().out
        assert "Place white and black stones" in captured
        assert detection_function is not None
        assert len(cutoffs) == 2


def test_update_board_metadata_new_board(capsys):
    with patch("builtins.open") as save, patch("json.dump"), patch("builtins.input", return_value=""), patch(
        "goban_irl.ui.interactive_corners"
    ) as corners:
        ui.update_board_metadata({"name": "name", "path": "path"})
        captured = capsys.readouterr().out
        assert "Making a new board (name)" in captured
        assert corners.called
        assert save.called

def test_update_board_metadata_existing_board():
    new_delay = '2'
    should_click = 'n'
    with patch("builtins.open") as save, patch("json.dump"), patch("builtins.input", side_effect=[new_delay, should_click]):
        sample_board_properties = {
            "name": "sample",
            "path": "sample2.json",
            "delay": 0,
            "loader_type": "virtual",
            "flip": False,
            "click": True,
            "corners": [[888, 248], [2470, 1830]],
            "detection_function": "check_max_difference",
            "cutoffs": [650, 750],
        }
        new_metadata = ui.update_board_metadata(sample_board_properties, fix_corners=False, fix_calibration=False, fix_delay=True, fix_click=True)
        assert new_metadata['delay'] == 2
        assert not new_metadata['click']
        assert save.called
        for key in sample_board_properties.keys():
            if key not in ["delay", "click"]:
                assert sample_board_properties[key] == new_metadata[key]

