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
    with patch("builtins.open") as save, patch("json.dump"), patch(
        "builtins.input", return_value=""
    ), patch("goban_irl.ui.interactive_corners") as corners:
        ui.update_board_metadata({"name": "name", "path": "path"})
        captured = capsys.readouterr().out
        assert "Making a new board (name)" in captured
        assert corners.called
        assert save.called


def test_update_board_metadata_existing_board():
    new_delay = "2"
    should_click = "n"
    with patch("builtins.open") as save, patch("json.dump"), patch(
        "builtins.input", side_effect=[new_delay, should_click]
    ):
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
        new_metadata = ui.update_board_metadata(
            sample_board_properties,
            fix_corners=False,
            fix_calibration=False,
            fix_delay=True,
            fix_click=True,
        )
        assert new_metadata["delay"] == 2
        assert not new_metadata["click"]
        assert save.called
        for key in sample_board_properties.keys():
            if key not in ["delay", "click"]:
                assert sample_board_properties[key] == new_metadata[key]


@patch("goban_irl.ui.load_existing_metadata", return_value=(None, True))
@patch("goban_irl.ui.update_board_metadata")
def test_update_handler(update, load):
    with patch("builtins.input", return_value="a"):
        ui.update_handler({})
        assert load.called
        assert update.call_args.kwargs["fix_calibration"]
        assert not update.call_args.kwargs["fix_corners"]

    with patch("builtins.input", return_value="o"):
        ui.update_handler({})
        assert update.call_args.kwargs["fix_corners"]
        assert not update.call_args.kwargs["fix_calibration"]

    with patch("builtins.input", return_value="d"):
        ui.update_handler({})
        assert update.call_args.kwargs["fix_delay"]
        assert not update.call_args.kwargs["fix_calibration"]

    with patch("builtins.input", return_value="c"):
        ui.update_handler({})
        assert update.call_args.kwargs["fix_click"]
        assert not update.call_args.kwargs["fix_calibration"]

    with patch("builtins.input", return_value="n"):
        ui.update_handler({})
        assert update.call_args.kwargs["fix_calibration"]
        assert update.call_args.kwargs["fix_corners"]
        assert update.call_args.kwargs["fix_delay"]
        assert update.call_args.kwargs["fix_click"]

    with patch("builtins.input", return_value="aodc"):
        ui.update_handler({})
        assert update.call_args.kwargs["fix_calibration"]
        assert update.call_args.kwargs["fix_corners"]
        assert update.call_args.kwargs["fix_delay"]
        assert update.call_args.kwargs["fix_click"]

    with patch("builtins.input", return_value="aodcnu"):
        ui.update_handler({})
        assert not update.call_args.kwargs["fix_calibration"]
        assert not update.call_args.kwargs["fix_corners"]
        assert not update.call_args.kwargs["fix_delay"]
        assert not update.call_args.kwargs["fix_click"]


@patch("goban_irl.ui.watch_boards")
@patch("goban_irl.ui.update_handler")
@patch("goban_irl.ui.run_app")
@patch("goban_irl.ui.fast_forward")
def test_exit_handler(fast_forward, run_app, update_handler, watch_boards):
    with patch("builtins.input", return_value="c"):
        ui.exit_handler({}, {})
        assert watch_boards.called

    with patch("builtins.input", return_value="f"):
        ui.exit_handler({"name": "first"}, {"name": "second"})
        assert update_handler.called
        assert update_handler.call_args.args[0] == {"name": "first"}

    with patch("builtins.input", return_value="s"):
        ui.exit_handler({"name": "first"}, {"name": "second"})
        assert update_handler.called
        assert update_handler.call_args.args[0] == {"name": "second"}

    with patch("builtins.input", return_value="r"):
        ui.exit_handler({}, {})
        assert run_app.called

    with patch("builtins.input", return_value="z"):
        ui.exit_handler({}, {})
        assert fast_forward.called


@patch("goban_irl.ui.click")
def test_play_stones_odd(click):
    """Check that when an odd number of stones play,
    up_next is the opposite color of the stone_to_play
    click is called
    """
    first_board = {}
    up_next = "black"
    screen_scale = 1

    stones_to_play = [(0, 0, "empty", "black")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == "white"
    assert click.called

    stones_to_play = [(0, 0, "empty", "white")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == "black"
    assert click.call_count == 2


@patch("goban_irl.ui.click")
def test_play_stones_even(click):
    """Check that when an even number of stones play,
    up_next is the same color of the stone_to_play
    click is called
    """
    first_board = {}
    up_next = "black"
    screen_scale = 1

    stones_to_play = [(0, 0, "empty", "black"), (1, 0, "empty", "white")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == up_next
    assert click.call_count == 2

    up_next = "white"
    stones_to_play = [(0, 0, "empty", "black"), (1, 0, "empty", "white")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == up_next
    assert click.call_count == 4


@patch("goban_irl.ui.click")
def test_play_stones_edge_cases(click):
    """Check that play stones overrides the arg play_next
    When there are odd stones to play
    """
    first_board = {}
    up_next = "white"
    screen_scale = 1

    stones_to_play = [(0, 0, "empty", "white")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=False
    )
    assert next_up == "white"
    assert not click.called

    stones_to_play = [(0, 0, "empty", "black")]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == "white"
    assert click.call_count == 1

    stones_to_play = [
        (0, 0, "empty", "black"),
        (0, 1, "empty", "white"),
        (1, 0, "empty", "black"),
    ]
    next_up = ui.play_stones(
        first_board, stones_to_play, up_next, screen_scale, play_odd=True
    )
    assert next_up == "white"
    assert click.call_count == 4


def test_evaluate_state():
    pass


def test_update_all_pending():
    pass


def test_get_board_name():
    pass


def test_watch_boards():
    pass


def test_run_app():
    pass
