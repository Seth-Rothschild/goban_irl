import json
import os
import itertools
import time

import pyautogui
import cv2
import numpy as np

from goban_irl.board import Board
from goban_irl.utilities import (
    check_bgr_blue,
    check_hsv_value,
    check_bw,
    check_bgr_and_bw,
)


def _boxify(string):
    """Takes a string and returns a nice ascii box"""
    horizontal_line = (len(string) + 4) * "-"
    return "+{}+\n|  {}  |\n+{}+\n\n".format(horizontal_line, string, horizontal_line)


def _print_missing(board, missing):
    human_readable_coordinates = []
    for row, col in missing:
        human_description = "{} - {}".format(
            board._human_readable_alpha((row, col)), board.state[row][col]
        )
        human_readable_coordinates.append(human_description)
    return human_readable_coordinates


def _print_welcome_message():
    welcome_message = _boxify("Welcome!")
    welcome_message += "This application is an example of how goban_irl\n"
    welcome_message += "can be used to interface between a digital and\n"
    welcome_message += "physical board.\n\n"
    print(welcome_message)


def _print_cornerloader_text(loader_type):
    cornerloader_text = ""
    if loader_type == "virtual":
        cornerloader_text += (
            "\nSelect TWO opposite corners of the board (e.g. (1, 1) and (19, 19).\n"
        )
        cornerloader_text += (
            "Selected points will appear as red circles once they are clicked.\n"
        )
        cornerloader_text += (
            "Once you've chosen two corners, you can exit the selector with Enter.\n\n"
        )

    elif loader_type == "physical":
        cornerloader_text += "\nSelect FOUR corners of the board.\n"
        cornerloader_text += (
            "Selected points will appear as red circles once they are clicked.\n"
        )
        cornerloader_text += (
            "Once you've chosen four corners, you can exit the selector with Enter.\n\n"
        )
    print(cornerloader_text)


def _print_loaded_boards(boards_metadata):
    loaded_boards_message = ""
    if boards_metadata is None:
        loaded_boards_message += "You have not created any boards yet."
    else:
        for i, board in enumerate(boards_metadata):
            loaded_boards_message += "Board {}:\n    loader = {},\n    corners = {},\n    boundaries = {}\n\n".format(
                i, board["loader_type"], board["corners"], board["cutoffs"]
            )
    print(loaded_boards_message)


def _print_describe_missing(board, missing_stones, board_name):
    if len(missing_stones) > 0:
        print("{} is missing stones".format(board_name))
        if len(missing_stones) > 5:
            print("    Missing many stones ({})".format(len(missing_stones)))
        else:
            for (row, col) in missing_stones:
                print(
                    "    Missing {} stone at {} ({})".format(
                        board.state[row][col],
                        board._human_readable_alpha((row, col)),
                        board._human_readable_numeric((row, col)),
                    )
                )
        print('')

def _load_detection_function(function_name):
    for function in [check_bgr_blue, check_hsv_value, check_bw, check_bgr_and_bw]:
        if function_name == function.__name__:
            return function


def _prompt_handler(prompt):
    true_options = ["y", "Y", "yes", "Yes", ""]
    false_options = ["n", "N", "no", "No"]
    response = input("{}: ".format(prompt))
    if response in true_options:
        return True
    elif response in false_options:
        return False
    else:
        print("Please input either {} or {}".format(true_options[0], false_options[0]))
        return _prompt_handler(prompt)


def _click(board, missing_stone_location, screen_scale=2):
    start_x, start_y = pyautogui.position()
    i, j = missing_stone_location
    screen_position = board.intersections[i][j]
    topleft = board.corners[0]
    click_location = [
        (screen_position[index] + topleft[index]) // screen_scale for index in range(2)
    ]
    pyautogui.moveTo(click_location[0], click_location[1])
    pyautogui.click()
    pyautogui.moveTo(start_x, start_y)


def _load_board_from_metadata(metadata, debug=False):
    detection_function = _load_detection_function(metadata["detection_function"])
    return Board(
        image=get_snapshot(metadata["loader_type"]),
        corners=metadata["corners"],
        detection_function=detection_function,
        cutoffs=metadata["cutoffs"],
        flip=metadata["flip"],
        debug=debug,
    )


def _show_sample_board(board_metadata):
    sample_board = _load_board_from_metadata(board_metadata, debug=True)


def _get_scale():
    img = pyautogui.screenshot()
    img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    height, width, _ = img.shape
    return height // pyautogui.size().height


def _show_boards_list():
    load_options = [f for f in os.listdir() if f.split(".")[-1] == "json"]
    if len(load_options) > 0:
        print("Existing boards:")
        for i, option in enumerate(load_options):
            print("    {}: {}".format(i, option))
        print("")
    return load_options


def _get_board_name(load_options, descriptor="board"):
    result = input("Choose a name for your {}: ".format(descriptor))
    if result.isnumeric():
        index = int(result)
        board_path = load_options[index]
        board_name = load_options[index].split(".")[0]
        use_existing = True

    elif result in load_options:
        board_path = result
        board_name = result.split(".")[0]
        use_existing = True

    elif (result + ".json") in load_options:
        board_name = result
        board_path = result + ".json"
        use_existing = True

    else:
        print("No board {} found, we can make a new one!\n".format(result))
        board_name = result
        board_path = result + ".json"
        use_existing = False

    if use_existing:
        use_existing = _prompt_handler(
            "Do you want to use the existing board ({})".format(board_name)
        )

    return board_name, board_path, use_existing


def _get_corners(img):
    title = "corners"
    corners = []

    def record_corners(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            corners.append((x, y))
            new_img = cv2.circle(img, (x, y), 20, (0, 0, 255), 2)
            cv2.imshow(title, new_img)

    cv2.namedWindow(title)
    cv2.setMouseCallback(title, record_corners)
    height, width, _ = img.shape
    img = cv2.resize(img, (int(width / 1.5), int(height / 1.5)))
    cv2.imshow(title, img)

    cv2.waitKey(10000)
    return [(int(x * 1.5), int(y * 1.5)) for (x, y) in corners]


def interactive_get_corners(loader_type):
    _print_cornerloader_text(loader_type)

    if loader_type == "virtual":
        ncorners = 2
        input("Make your board visible on screen and press enter to continue...")
    elif loader_type == "physical":
        ncorners = 4
        input(
            "Position your camera to clearly see the board and press enter to continue..."
        )

    corners = []
    while len(corners) != ncorners:
        snapshot = get_snapshot(loader_type)
        corners = _get_corners(snapshot)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    return corners


def make_board(board_name, board_path):
    print("Making a new board ({})...".format(board_name))
    if _prompt_handler("Is this a virtual board?"):
        loader_type = "virtual"
        flip = False
    else:
        loader_type = "physical"
        flip = True

    corners = interactive_get_corners(loader_type)

    if _prompt_handler("Would you like to calibrate?"):
        detection_function, cutoffs = iteractive_calibrate(second_board_metadata)
    else:
        detection_function = check_bgr_and_bw
        cutoffs = (204, 316)

    board_metadata = {
        "loader_type": loader_type,
        "corners": corners,
        "detection_function": detection_function.__name__,
        "cutoffs": cutoffs,
        "flip": flip,
    }

    with open(board_path, "w") as f:
        json.dump(board_metadata, f)

    return board_metadata


def interactive_calibrate(board_metadata):
    snapshot = get_snapshot(board_metadata["loader_type"])
    corners = board_metadata["corners"]
    board = Board(snapshot, corners)

    input(
        "Place white stones at every corner and black stones inside, and no other stones then press Enter"
    )

    black_stones = [(17, 17), (1, 1), (1, 17), (17, 1)]
    white_stones = [(18, 18), (0, 0), (18, 0), (0, 18)]
    empty_spaces = [
        x
        for x in set(list(itertools.combinations(list(range(19)) + list(range(19)), 2)))
        if ((x not in white_stones) and (x not in black_stones))
    ]
    detection_function, cutoffs = board.calibrate(
        black_stones=black_stones,
        white_stones=white_stones,
        empty_spaces=empty_spaces,
        verbose=True,
    )
    if detection_function is None:
        raise ValueError("Calibration failed, exiting.")

    return detection_function, cutoffs


def get_snapshot(loader_type):
    if loader_type == "virtual":
        img = pyautogui.screenshot()
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        height, width, _ = img.shape
        return img

    elif loader_type == "physical":
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise IOError("Cannot open webcam")
        _, frame = cap.read()
        return frame


def run_app(verbose_output=False, show_sample=False):
    _print_welcome_message()

    load_options = _show_boards_list()
    first_board_name, first_board_path, use_existing_first_board = _get_board_name(
        load_options, "first board"
    )
    second_board_name, second_board_path, use_existing_second_board = _get_board_name(
        load_options, "second board"
    )

    if use_existing_first_board:
        with open(first_board_path) as f:
            first_board_metadata = json.load(f)
    else:
        first_board_metadata = make_board(first_board_name, first_board_path)

    if use_existing_second_board:
        with open(second_board_path) as f:
            second_board_metadata = json.load(f)
    else:
        second_board_metadata = make_board(second_board_name, second_board_path)

    _print_loaded_boards([first_board_metadata, second_board_metadata])

    screen_scale = _get_scale()
    previous_missing_stones = [[], []]

    while True:
        first_board = _load_board_from_metadata(first_board_metadata)
        second_board = _load_board_from_metadata(second_board_metadata)

        first_board_missing_stones = first_board.compare_to(second_board)
        second_board_missing_stones = second_board.compare_to(first_board)

        if (
            first_board_missing_stones != previous_missing_stones[0]
            or second_board_missing_stones != previous_missing_stones[1]
        ):
            previous_missing_stones = [
                first_board_missing_stones,
                second_board_missing_stones,
            ]

            if verbose_output:
                _print_describe_missing(
                    first_board, second_board_missing_stones, second_board_name
                )
                _print_describe_missing(
                    second_board, first_board_missing_stones, first_board_name
                )
                if len(first_board_missing_stones) == 0 and len(second_board_missing_stones) == 0:
                    print('Board states match.\n')

        if len(first_board_missing_stones) == 1:
            _click(
                first_board, first_board_missing_stones[0], screen_scale=screen_scale
            )


if __name__ == "__main__":
    try:
        run_app(verbose_output=True, show_sample=False)
    except KeyboardInterrupt:
        print("\nExiting, thanks for playing!")
