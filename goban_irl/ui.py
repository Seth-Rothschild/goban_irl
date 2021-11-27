import json
import os
import itertools
import time

import pyautogui
import cv2
import numpy as np
import mss

from goban_irl.board import Board
import goban_irl.utilities as utils


def _boxify(string):
    """Takes a string and returns a nice ascii box"""
    horizontal_line = (len(string) + 4) * "-"
    return "+{}+\n|  {}  |\n+{}+\n\n".format(horizontal_line, string, horizontal_line)


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
            loaded_boards_message += "Board {} ({}):\n".format(i + 1, board["name"])
            for key, value in board.items():
                loaded_boards_message += "    {} = {}\n".format(key, value)
            loaded_boards_message += "\n"

    print(loaded_boards_message)


def _print_describe_missing(
    mismatched_stones, this_board_name="Board 1", other_board_name="Board 2"
):
    if len(mismatched_stones) == 0:
        print("Board states match!\n")
        return

    this_board_missing = [x for x in mismatched_stones if x[2] == "empty"]
    other_board_missing = [x for x in mismatched_stones if x[3] == "empty"]
    misplay = [x for x in mismatched_stones if (x[2] != "empty") and (x[3] != "empty")]
    board = Board()

    if len(misplay) > 0:
        if len(misplay) > 5:
            print("Warning! There are many mismatched stones ({})".format(len(misplay)))
        else:
            print("Warning! There are mismatched stones:")
            for (i, j, this_stone, other_stone) in misplay:
                print(
                    "    At {} ({}) {} has {} and {} has {}".format(
                        board._human_readable_alpha((i, j)),
                        board._human_readable_numeric((i, j)),
                        this_board_name,
                        this_stone,
                        other_board_name,
                        other_stone,
                    )
                )
        return

    if len(this_board_missing) > 0:
        if len(this_board_missing) > 5:
            print(
                "{} is missing many stones ({})".format(
                    this_board_name, len(this_board_missing)
                )
            )
        else:
            print("{} is missing stones:".format(this_board_name))
            for (i, j, _, other_stone) in this_board_missing:
                print(
                    "    Missing {} stone at {} ({})".format(
                        other_stone,
                        board._human_readable_alpha((i, j)),
                        board._human_readable_numeric((i, j)),
                    )
                )
            print("")

    if len(other_board_missing) > 0:
        if len(other_board_missing) > 5:
            print(
                "{} is missing many stones ({})".format(
                    other_board_name, len(other_board_missing)
                )
            )
        else:
            print("{} is missing stones:".format(other_board_name))
            for (i, j, this_stone, _) in other_board_missing:
                print(
                    "    Missing {} stone at {} ({})".format(
                        this_stone,
                        board._human_readable_alpha((i, j)),
                        board._human_readable_numeric((i, j)),
                    )
                )
            print("")


def _load_detection_function(function_name):
    for function in [
        utils.check_bgr_blue,
        utils.check_hsv_value,
        utils.check_bw,
        utils.check_bgr_and_bw,
        utils.check_bw_subimage,
        utils.check_max_difference,
        utils.check_subimage_max_difference,
        utils.check_bgr_subimage,
        utils.check_sum,
    ]:
        if function_name == function.__name__:
            return function
    raise ValueError("Detection function {} not loaded".format(function_name))


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
    i, j, _, _ = missing_stone_location
    screen_position = board.intersections[i][j]
    topleft = board.corners[0]
    click_location = [
        (screen_position[index] + topleft[index]) // screen_scale for index in range(2)
    ]
    pyautogui.moveTo(click_location[0], click_location[1])
    pyautogui.click()
    pyautogui.moveTo(start_x, start_y)


def _load_board_from_metadata(metadata, sct=None, debug=False):
    detection_function = _load_detection_function(metadata["detection_function"])
    return Board(
        image=get_snapshot(metadata["loader_type"], sct=sct),
        corners=metadata["corners"],
        detection_function=detection_function,
        cutoffs=metadata["cutoffs"],
        flip=metadata["flip"],
        debug=debug,
    )


def _show_sample_board(board_metadata):
    sample_board = _load_board_from_metadata(board_metadata, debug=True)


def _get_scale():
    img = get_snapshot("virtual")
    height, width, _ = img.shape
    return height // pyautogui.size().height


def _show_boards_list():
    load_options = [f for f in os.listdir() if f.split(".")[-1] == "json"]
    if len(load_options) > 0:
        print("Existing boards:")
        for i, option in enumerate(load_options):
            print("    {}: {}".format(i + 1, option))
        print("")
    return load_options


def _get_board_name(load_options, descriptor="board"):
    result = input("Choose a name for your {}: ".format(descriptor))
    if result.isnumeric():
        index = int(result) - 1
        board_path = load_options[index]
        board_name = load_options[index].split(".")[0]
        exists = True

    elif result in load_options:
        board_path = result
        board_name = result.split(".")[0]
        exists = True

    elif (result + ".json") in load_options:
        board_name = result
        board_path = result + ".json"
        exists = True

    else:
        print("No board {} found, we can make a new one!\n".format(result))
        board_name = result
        board_path = result + ".json"
        exists = False

    return board_name, board_path, exists


def _get_clicks(img):
    title = "registering clicks"
    intersections = []

    def record_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            intersections.append((x, y))
            new_img = cv2.circle(img, (x, y), 20, (0, 0, 255), 2)
            cv2.imshow(title, new_img)

    cv2.namedWindow(title)
    cv2.setMouseCallback(title, record_click)
    height, width, _ = img.shape
    img = cv2.resize(img, (int(width / 1.5), int(height / 1.5)))
    cv2.imshow(title, img)

    cv2.waitKey(10000)
    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)

    return [(int(x * 1.5), int(y * 1.5)) for (x, y) in intersections]


def interactive_get_corners(loader_type):
    _print_cornerloader_text(loader_type)

    if loader_type == "virtual":
        input("Make your board visible on screen and press enter to continue...")
    elif loader_type == "physical":
        input(
            "Position your camera to clearly see the board and press enter to continue..."
        )

    corners = []
    while len(set(corners)) != 2 and len(set(corners)) != 4:
        snapshot = get_snapshot(loader_type)
        corners = _get_clicks(snapshot)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)

    return list(set(corners))


def make_board(board_metadata, fix_corners=True, fix_calibration=True, fix_delay=False):
    board_name = board_metadata["name"]
    board_path = board_metadata["path"]

    if len(list(board_metadata.keys())) == 2:
        print("Making a new board ({})...".format(board_name))
        if _prompt_handler("Is this a virtual board?"):
            loader_type = "virtual"
            flip = False
            delay = 0
        else:
            loader_type = "physical"
            flip = True
            delay = 2
    else:

        loader_type = board_metadata["loader_type"]
        flip = board_metadata["flip"]
        delay = board_metadata["delay"]

        corners = board_metadata["corners"]
        detection_function = board_metadata["detection_function"]
        cutoffs = board_metadata["cutoffs"]

    if fix_corners:
        corners = interactive_get_corners(loader_type)

    if fix_calibration:
        if _prompt_handler("Would you like to use the default calibration?"):
            detection_function = utils.check_max_difference.__name__
            cutoffs = (650, 750)
        else:

            detection_function, cutoffs = interactive_calibrate(corners, loader_type)
            detection_function = detection_function.__name__
    if fix_delay:
        delay_str = input('What delay would you like (in seconds)? ')
        if delay_str == '':
            delay = 0
        elif delay_str.isnumeric():
            delay = float(delay_str)

    board_metadata = {
        "name": board_name,
        "path": board_path,
        "loader_type": loader_type,
        "corners": corners,
        "detection_function": detection_function,
        "cutoffs": cutoffs,
        "flip": flip,
        "delay": delay
    }

    with open(board_path, "w") as f:
        json.dump(board_metadata, f)

    return board_metadata


def _find_nearest_intersection(xstep, ystep, click):
    return (round(click[1] / ystep), round(click[0] / xstep))


def interactive_calibrate(corners, loader_type):
    snapshot = get_snapshot(loader_type)
    board = Board(snapshot, corners)

    print("Place white stones and black stones on the board.")
    print(
        "In the next three screens, click intersections with black stones, then white stones, then empty spaces"
    )
    input("Press Enter to continue...")

    black_clicks = _get_clicks(board.board_subimage)
    white_clicks = _get_clicks(board.board_subimage)
    empty_clicks = _get_clicks(board.board_subimage)

    _, _, xstep, ystep = board._get_board_params(board.board_subimage)
    black_stones = [
        _find_nearest_intersection(xstep, ystep, click) for click in black_clicks
    ]
    white_stones = [
        _find_nearest_intersection(xstep, ystep, click) for click in white_clicks
    ]
    empty_spaces = [
        _find_nearest_intersection(xstep, ystep, click) for click in empty_clicks
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


def get_snapshot(loader_type, sct=None):
    if loader_type == "virtual":
        if sct == None:
            with mss.mss() as sct:
                img = np.array(sct.grab(sct.monitors[1]))
        else:
            img = np.array(sct.grab(sct.monitors[1]))
        height, width, _ = img.shape
        return img

    elif loader_type == "physical":
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise IOError("Cannot open webcam")
        _, frame = cap.read()
        return frame


def _exit_handler(first_board_metadata, second_board_metadata):
    print("\nBoard Scanning Paused")
    print("Would you like to (c)ontinue, (l)oad new boards, (f)ast forward, or (e)xit?")
    try:
        response = input(">> ")
        if response == "c":
            watch_boards(first_board_metadata, second_board_metadata)

        elif response == "l":
            run_app()

        elif response == "f":
            fast_forward(first_board_metadata, second_board_metadata)
            watch_boards(first_board_metadata, second_board_metadata)

        else:
            print("\nExiting, thanks for playing!")
    except KeyboardInterrupt:
        print("\nExiting, thanks for playing!")


def play_stones(first_board, stones_to_play, up_next, screen_scale):
    black_stones_to_play = [
        (i, j, this_board_stone, other_board_stone)
        for (i, j, this_board_stone, other_board_stone) in stones_to_play
        if (this_board_stone == "empty" and other_board_stone == "black")
    ]
    white_stones_to_play = [
        (i, j, this_board_stone, other_board_stone)
        for (i, j, this_board_stone, other_board_stone) in stones_to_play
        if (this_board_stone == "empty" and other_board_stone == "white")
    ]

    max_stones_to_alternate = min(len(black_stones_to_play), len(white_stones_to_play))

    if up_next == "black":
        for i in range(max_stones_to_alternate):
            _click(first_board, black_stones_to_play[i], screen_scale)
            _click(first_board, white_stones_to_play[i], screen_scale)

    elif up_next == "white":
        for i in range(max_stones_to_alternate):
            _click(first_board, white_stones_to_play[i], screen_scale)
            _click(first_board, black_stones_to_play[i], screen_scale)

    if len(black_stones_to_play) == (len(white_stones_to_play) + 1):
        _click(first_board, black_stones_to_play[-1], screen_scale)
        up_next = "white"

    elif len(white_stones_to_play) == (len(black_stones_to_play) + 1):
        _click(first_board, white_stones_to_play[-1], screen_scale)
        up_next = "black"

    return up_next


def watch_boards(first_board_metadata, second_board_metadata):
    try:
        screen_scale = _get_scale()
        print("Watching boards! Press C-c to quit.")

        up_next = "black"
        previous_mismatched_stones = None
        all_pending = []
        with mss.mss() as sct:
            while True:
                first_board = _load_board_from_metadata(first_board_metadata, sct=sct)
                second_board = _load_board_from_metadata(second_board_metadata, sct=sct)
                mismatched_stones = first_board.compare_to(second_board)

                if previous_mismatched_stones != mismatched_stones:
                    _print_describe_missing(
                        mismatched_stones,
                        first_board_metadata["name"],
                        second_board_metadata["name"],
                    )
                    previous_mismatched_stones = mismatched_stones

                current_time = time.time()

                first_board_missing_stones = [
                    (i, j, this_board_stone, other_board_stone)
                    for (i, j, this_board_stone, other_board_stone) in mismatched_stones
                    if (this_board_stone == "empty")
                ]

                all_pending_stones = [stone for (stone, _) in all_pending]
                new_missing_stones = [
                    (stone, current_time)
                    for stone in first_board_missing_stones
                    if (stone not in all_pending_stones)
                ]

                if len(new_missing_stones) > 2:
                    continue

                else:
                    all_pending = [
                        (stone, first_seen)
                        for (stone, first_seen) in all_pending
                        if (stone in first_board_missing_stones)
                    ] + new_missing_stones

                    to_play = [
                        stone
                        for (stone, first_seen) in all_pending
                        if (current_time - first_seen > first_board_metadata["delay"])
                        and (stone in first_board_missing_stones)
                    ]

                    all_pending = [
                        (stone, first_seen)
                        for (stone, first_seen) in all_pending
                        if (stone, first_seen) not in to_play
                    ]

                    up_next = play_stones(first_board, to_play, up_next, screen_scale)

    except KeyboardInterrupt:
        _exit_handler(first_board_metadata, second_board_metadata)


def fast_forward(first_board_metadata, second_board_metadata):
    screen_scale = _get_scale()
    first_board = _load_board_from_metadata(first_board_metadata)
    second_board = _load_board_from_metadata(second_board_metadata)
    mismatched_stones = first_board.compare_to(second_board)

    stones_to_play = [
        (i, j, this_board_stone, other_board_stone)
        for (i, j, this_board_stone, other_board_stone) in mismatched_stones
        if (this_board_stone == "empty")
    ]

    play_stones(first_board, stones_to_play, "black", screen_scale)


def _fix_handler(board_metadata):
    print("Would you like to fix\n  c(o)rners,\n  c(a)libration,\n  (d)elay\n  [default: (n)ew board]")
    modify_choice = input(">>")

    fix_corners = False
    fix_calibration = False
    fix_delay = False

    if "a" in modify_choice:
        fix_calibration = True

    if "o" in modify_choice:
        fix_corners = True

    if "d" in modify_choice:
        fix_delay = True
    
    if "n" in modify_choice or modify_choice == '':
        fix_corners = True
        fix_calibration = True
        fix_delay = True

    board_metadata = make_board(
        board_metadata,
        fix_corners=fix_corners,
        fix_calibration=fix_calibration,
        fix_delay=fix_delay
    )

    return board_metadata


def run_app():
    _print_welcome_message()

    load_options = _show_boards_list()
    first_board_name, first_board_path, first_board_exists = _get_board_name(
        load_options, "first board"
    )
    (
        second_board_name,
        second_board_path,
        second_board_exists,
    ) = _get_board_name(load_options, "second board")

    if first_board_exists:
        with open(first_board_path) as f:
            first_board_metadata = json.load(f)
        _print_loaded_boards([first_board_metadata])

        use_existing = _prompt_handler(
            "Would you like to use the existing board ({}) as is".format(
                first_board_name
            )
        )
        if not use_existing:
            first_board_metadata = _fix_handler(first_board_metadata)
    else:
        first_board_metadata = {"name": first_board_name, "path": first_board_path}
        first_board_metadata = make_board(first_board_metadata)

    if second_board_exists:
        with open(second_board_path) as f:
            second_board_metadata = json.load(f)
        _print_loaded_boards([second_board_metadata])
        use_existing = _prompt_handler(
            "Would you like to use the existing board ({}) as is".format(
                second_board_name
            )
        )

        if not use_existing:
            second_board_metadata = _fix_handler(second_board_metadata)

    else:
        second_board_metadata = {"name": second_board_name, "path": second_board_path}
        second_board_metadata = make_board(second_board_metadata)

    watch_boards(first_board_metadata, second_board_metadata)


if __name__ == "__main__":
    run_app()
