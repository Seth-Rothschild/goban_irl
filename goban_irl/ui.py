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
    check_bgr_and_bw
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


def _print_cornerloader_text(board_metadata):
    cornerloader_text = ""
    if board_metadata["loader_type"] == "virtual":
        cornerloader_text += (
            "\nSelect TWO opposite corners of the board (e.g. (1, 1) and (19, 19).\n"
        )
        cornerloader_text += (
            "Selected points will appear as red circles once they are clicked.\n"
        )
        cornerloader_text += (
            "Once you've chosen two corners, you can exit the selector with Enter.\n\n"
        )

    elif board_metadata["loader_type"] == "physical":
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
        _prompt_handler(prompt)


def _click(board, missing_stone_location):
    start_x, start_y = pyautogui.position()
    i, j = missing_stone_location
    screen_position = board.intersections[i][j]
    topleft = board.corners[0]
    click_location = [
        (screen_position[index] + topleft[index]) // 2 for index in range(2)
    ]
    pyautogui.moveTo(click_location[0], click_location[1])
    pyautogui.click()
    pyautogui.moveTo(start_x, start_y)



def _load_board_from_metadata(metadata, debug=False):
    detection_function = _load_detection_function(metadata["detection_function"])
    return Board(
        image=ImageLoader(metadata["loader_type"]).snapshot(),
        corners=metadata["corners"],
        detection_function=detection_function,
        cutoffs=metadata["cutoffs"],
        flip=metadata["flip"],
        debug=debug
    )

def _show_sample_board(board_metadata):
    sample_board = _load_board_from_metadata(board_metadata, debug=True)

def load_corners(board_metadata):
    loader_type = board_metadata["loader_type"]
    loader = ImageLoader(loader_type)

    if loader_type == "virtual":
        ncorners = 2
    elif loader_type == "physical":
        ncorners = 4

    _print_cornerloader_text(board_metadata)
    input("Make your board visible on screen and press enter to continue...")

    corners = []
    img = loader.snapshot()

    while len(corners) != ncorners:
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        img = loader.snapshot()
        corners = get_corners(img)

    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)

    return corners

def run_app(verbose_output=False, show_sample=False):
    _print_welcome_message()

    first_board_name = input('Choose a name for your first board: ')
    if first_board_name == '':
        first_board_name='first_board'
    first_board_path = first_board_name + '.json'
    
    first_board_exists = os.path.exists(first_board_path)

    use_existing_first_board = False
    if first_board_exists:
        use_existing_first_board = _prompt_handler(
            "Do you want to use the existing board ({})?".format(first_board_name),
        )

    if first_board_exists and use_existing_first_board:
        with open(first_board_path) as f:
            first_board_metadata = json.load(f)
    else:
        first_board_metadata = {"loader_type": "virtual"}
        first_board_metadata["corners"] = load_corners(first_board_metadata)
        first_board_metadata["detection_function"] = 'check_bgr_and_bw'
        first_board_metadata["cutoffs"] = (204, 316)
        first_board_metadata["flip"] = False
        with open(first_board_path, "w") as f:
            json.dump(first_board_metadata, f)

    if show_sample:
        _show_sample_board(first_board_metadata)

        looks_ok = _prompt_handler(
            "Did the previous two images look correct? If not, we'll exit so you can start over.",
        )

        if not looks_ok:
            raise ValueError("Board looks off, exiting to start over!")

    second_board_name = input('Choose a name for your second board: ')
    if second_board_name == '':
        second_board_name = 'second_board'
    second_board_path = second_board_name + '.json'
    second_board_exists = os.path.exists(second_board_path)
    use_existing_second_board = False
    if second_board_exists:
        use_existing_second_board = _prompt_handler(
            "Do you want to use the existing board ({})?".format(second_board_name),
        )
    if second_board_exists and use_existing_second_board:
        with open(second_board_path) as f:
            second_board_metadata = json.load(f)
    else:
        if _prompt_handler('Is this a physical board?'):
            loader_type = "physical"
            flip = True
        else:
            loader_type = "virtual"
            flip = False

        second_board_metadata = {"loader_type": loader_type}
        second_board_metadata["corners"] = load_corners(second_board_metadata)
        
        if _prompt_handler('Would you like to calibrate?'):
            detection_function, cutoffs = calibrate(second_board_metadata)
        else:
            detection_function = check_bgr_and_bw
            cutoffs = (204, 316)
        
        second_board_metadata["detection_function"] = detection_function.__name__
        second_board_metadata["cutoffs"] = cutoffs
        second_board_metadata["flip"] = flip

        with open(second_board_path, "w") as f:
            json.dump(second_board_metadata, f)

    if show_sample:
        _show_sample_board(second_board_metadata)

        looks_ok = _prompt_handler(
            "Did the previous two images look correct? If not, we'll exit so you can start over.",
        )

        if not looks_ok:
            raise ValueError("Board looks off, exiting to start over!")

    _print_loaded_boards([first_board_metadata, second_board_metadata])

    while True:
        first_board = _load_board_from_metadata(first_board_metadata)
        second_board = _load_board_from_metadata(second_board_metadata)

        first_board_missing_stones = first_board.compare_to(second_board)
        second_board_missing_stones = second_board.compare_to(first_board)

        if verbose_output:
            _print_describe_missing(
                first_board, second_board_missing_stones, second_board_name
            )
            _print_describe_missing(
                second_board, first_board_missing_stones, first_board_name
            )

        if (
            len(first_board_missing_stones) == 1
        ):
            _click(first_board, first_board_missing_stones[0])
        time.sleep(.5)


def get_corners(img):
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


def calibrate(board_metadata):
    loader = ImageLoader(board_metadata["loader_type"])
    corners = board_metadata["corners"]
    board = Board(loader.snapshot(), corners)

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
        black_stones=black_stones, white_stones=white_stones, empty_spaces=empty_spaces, verbose=True
    )
    if detection_function is None:
        raise ValueError("Calibration failed, exiting.")

    return detection_function, cutoffs


class ImageLoader:
    def __init__(self, board_type):
        self.board_type = board_type

    def snapshot(self):
        if self.board_type == "virtual":
            img = pyautogui.screenshot()
            img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            height, width, _ = img.shape

            return img

        elif self.board_type == "physical":
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                raise IOError("Cannot open webcam")
            _, frame = cap.read()
            #height, width, _ = frame.shape
            #img = cv2.resize(frame, (int(width / 3), int(height / 3)))
            #cv2.imshow('camera', img)
            #cv2.waitKey(1)

            
            return frame


if __name__ == "__main__":
    run_app(verbose_output=True, show_sample=False)
