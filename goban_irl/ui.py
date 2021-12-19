import json
import os
import time
import mss


from goban_irl.board import Board
from goban_irl.helpers import (
    boxify,
    prompt_handler,
    get_scale,
    get_nearest_intersection,
    click,
    print_describe_missing,
)
import goban_irl.opencv_utilities as utils


def welcome_message():
    welcome_message = boxify("Welcome!")
    welcome_message += "This application is an example of how goban_irl can be used\n"
    welcome_message += "to interface between multiple boards."
    print(welcome_message)


def cornerloader_text():
    cornerloader_text = "Select two or four corners of the board. Selected points\n"
    cornerloader_text += "will appear as red circles once they are clicked. Once\n"
    cornerloader_text += "you are done, you can hit Enter to continue."
    print(cornerloader_text)


def calibrate_text():
    calibrate_text = "Place white and black stones on the board. You will have\n"
    calibrate_text += "10 seconds on each of the next three screens to click\n"
    calibrate_text += "black stones, white stones, and empty spaces in that order."
    print(calibrate_text)


def show_boards_list():
    load_options = [f for f in os.listdir() if f.split(".")[-1] == "json"]
    if len(load_options) > 0:
        print("Existing boards:")
        for i, option in enumerate(load_options):
            print("    {}: {}".format(i + 1, option))
        print("")
    return load_options


def load_existing_metadata(board_metadata):
    if os.path.exists(board_metadata["path"]):
        with open(board_metadata["path"]) as f:
            board_metadata = json.load(f)
        loaded_boards_message = ""
        loaded_boards_message += "Board ({}):\n".format(board_metadata["name"])
        for key, value in board_metadata.items():
            loaded_boards_message += "    {} = {}\n".format(key, value)
        loaded_boards_message += "\n"
        print(loaded_boards_message)
        return board_metadata, True
    else:
        return board_metadata, False


def load_board_from_metadata(metadata, sct=None, debug=False):
    detection_function = utils.load_detection_function(metadata["detection_function"])
    return Board(
        image=utils.get_snapshot(metadata["loader_type"], sct=sct),
        corners=metadata["corners"],
        detection_function=detection_function,
        cutoffs=metadata["cutoffs"],
        flip=metadata["flip"],
        debug=debug,
    )


def interactive_corners(loader_type):
    cornerloader_text()

    if loader_type == "virtual":
        input("Make your board visible on screen and press enter to continue...")
    elif loader_type == "physical":
        input(
            "Position your camera to clearly see the board and press enter to continue..."
        )

    corners = []
    while len(set(corners)) != 2 and len(set(corners)) != 4:
        snapshot = utils.get_snapshot(loader_type)
        corners = utils.get_clicks(snapshot)

    return list(set(corners))


def interactive_calibrate(corners, loader_type):
    calibrate_text()
    input("Press Enter to continue...")
    snapshot = utils.get_snapshot(loader_type)
    board = Board(snapshot, corners)

    black_clicks = utils.get_clicks(board.board_subimage)
    white_clicks = utils.get_clicks(board.board_subimage)
    empty_clicks = utils.get_clicks(board.board_subimage)

    _, _, xstep, ystep = board._get_board_params(board.board_subimage)
    black_stones = [
        get_nearest_intersection(xstep, ystep, click) for click in black_clicks
    ]
    white_stones = [
        get_nearest_intersection(xstep, ystep, click) for click in white_clicks
    ]
    empty_spaces = [
        get_nearest_intersection(xstep, ystep, click) for click in empty_clicks
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


def update_board_metadata(
    board_metadata,
    fix_corners=True,
    fix_calibration=True,
    fix_delay=False,
    fix_click=False,
):
    new_metadata = {**board_metadata}

    if len(list(new_metadata.keys())) == 2:
        print("Making a new board ({})...".format(new_metadata["name"]))
        fix_corners = True
        fix_calibration = True

        new_metadata["delay"] = 0
        if prompt_handler("Is this a virtual board?"):
            new_metadata["loader_type"] = "virtual"
            new_metadata["flip"] = False
            new_metadata["click"] = True

        else:
            new_metadata["loader_type"] = "physical"
            new_metadata["flip"] = True
            new_metadata["click"] = False

    if fix_corners:
        new_metadata["corners"] = interactive_corners(new_metadata["loader_type"])

    if fix_calibration:
        if prompt_handler("Would you like to use the default calibration?"):
            new_metadata["detection_function"] = utils.check_max_difference.__name__
            new_metadata["cutoffs"] = (650, 750)
        else:
            detection_function, new_metadata["cutoffs"] = interactive_calibrate(
                new_metadata["corners"], new_metadata["loader_type"]
            )
            new_metadata["detection_function"] = detection_function.__name__

    if fix_delay:
        delay_str = input("What delay would you like (in seconds)? ")
        if delay_str == "":
            new_metadata["delay"] = 0
        elif delay_str.isnumeric():
            new_metadata["delay"] = float(delay_str)

    if fix_click:
        new_metadata["click"] = prompt_handler(
            "Would you like this program to autoclick on the screen location?"
        )

    with open(new_metadata["path"], "w") as f:
        json.dump(new_metadata, f)

    return new_metadata


def update_handler(board_metadata):
    board_metadata, board_exists = load_existing_metadata(board_metadata)

    modify_choice = ""
    if board_exists:
        options = [
            "Update Options:",
            "c(a)libration",
            "c(o)rners",
            "(d)elay",
            "(c)lick",
            "(n)ew board",
            "(u)se as is (default)",
        ]
        print("\n    ".join(options))
        modify_choice = input(">>")

    fix_corners = False
    fix_calibration = False
    fix_delay = False
    fix_click = False

    if "a" in modify_choice:
        fix_calibration = True

    if "o" in modify_choice:
        fix_corners = True

    if "d" in modify_choice:
        fix_delay = True
    if "c" in modify_choice:
        fix_click = True

    if "n" in modify_choice:
        fix_corners = True
        fix_calibration = True
        fix_delay = True
        fix_click = True

    if "u" in modify_choice or "" == modify_choice:
        fix_corners = False
        fix_calibration = False
        fix_delay = False
        fix_click = False

    board_metadata = update_board_metadata(
        board_metadata,
        fix_corners=fix_corners,
        fix_calibration=fix_calibration,
        fix_delay=fix_delay,
        fix_click=fix_click,
    )

    return board_metadata


def exit_handler(first_board_metadata, second_board_metadata):
    print("\nBoard Scanning Paused")
    options = [
        "Options:",
        "(c)ontinue",
        "(f)irst board needs update",
        "(s)econd board needs update",
        "(r)estart app",
        "(z)oom state forward",
        "(e)xit",
    ]
    print("\n    ".join(options))

    try:
        response = input(">> ")
        if response == "c":
            watch_boards(first_board_metadata, second_board_metadata)

        elif response == "f" or response == "1":
            print("Updating first board...")
            first_board_metadata = update_handler(first_board_metadata)
            watch_boards(first_board_metadata, second_board_metadata)

        elif response == "s" or response == "2":
            print("Updating second board...")
            second_board_metadata = update_handler(second_board_metadata)
            watch_boards(first_board_metadata, second_board_metadata)

        elif response == "r":
            run_app()

        elif response == "z":
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
            click(first_board, black_stones_to_play[i], screen_scale)
            click(first_board, white_stones_to_play[i], screen_scale)

    elif up_next == "white":
        for i in range(max_stones_to_alternate):
            click(first_board, white_stones_to_play[i], screen_scale)
            click(first_board, black_stones_to_play[i], screen_scale)

    if len(black_stones_to_play) == (len(white_stones_to_play) + 1):
        click(first_board, black_stones_to_play[-1], screen_scale)
        up_next = "white"

    elif len(white_stones_to_play) == (len(black_stones_to_play) + 1):
        click(first_board, white_stones_to_play[-1], screen_scale)
        up_next = "black"

    return up_next


def fast_forward(first_board_metadata, second_board_metadata):
    screen_scale = get_scale()
    first_board = load_board_from_metadata(first_board_metadata)
    second_board = load_board_from_metadata(second_board_metadata)
    mismatched_stones = first_board.compare_to(second_board)

    stones_to_play = [
        (i, j, this_board_stone, other_board_stone)
        for (i, j, this_board_stone, other_board_stone) in mismatched_stones
        if (this_board_stone == "empty")
    ]

    play_stones(first_board, stones_to_play, "black", screen_scale)


def evaluate_state(first_board, second_board, all_pending):
    mismatched_stones = first_board.compare_to(second_board)
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
    return first_board_missing_stones, new_missing_stones


def update_all_pending(
    all_pending, first_board_missing_stones, new_missing_stones, delay
):
    all_pending = [
        (stone, first_seen)
        for (stone, first_seen) in all_pending
        if (stone in first_board_missing_stones)
    ] + new_missing_stones
    to_play = [
        stone
        for (stone, first_seen) in all_pending
        if (time.time() - first_seen > delay) and (stone in first_board_missing_stones)
    ]
    all_pending = [
        (stone, first_seen)
        for (stone, first_seen) in all_pending
        if stone not in to_play
    ]
    return all_pending, to_play


def get_board_name(load_options, descriptor="board"):
    """Prompt to ask for a board name.

    Args:
        load_options: A list of json files in a target directory

    Returns:
        (board_name, board_path, board_exists)
    """
    result = input("Choose a name for your {}: ".format(descriptor))
    if result.isnumeric():
        index = int(result) - 1
        board_path = load_options[index]
        board_name = load_options[index].split(".")[0]

    elif result in load_options:
        board_path = result
        board_name = result.split(".")[0]

    elif (result + ".json") in load_options:
        board_name = result
        board_path = result + ".json"

    elif result == "":
        board_name = "{}".format(descriptor)
        board_path = "{}.json".format(descriptor)

    else:
        print("No board {} found, we can make a new one!\n".format(result))
        board_name = result
        board_path = result + ".json"

    return {"name": board_name, "path": board_path}


def watch_boards(first_board_metadata, second_board_metadata):
    """Continuously scan two boards.

    If keyboard interrupted, pause and give user some options.

    Args:
        first_board_metadata (dict): A dictionary with enough information to load the first board
        second_board_metadata (dict): A dictionary with enough information to load the second board

    """
    try:
        screen_scale = get_scale()
        print("Watching boards! Press C-c to quit.")

        up_next = "black"
        all_pending = []
        previous_missing_stones = []
        delay = first_board_metadata["delay"]

        with mss.mss() as sct:
            while True:
                first_board = load_board_from_metadata(first_board_metadata, sct=sct)
                second_board = load_board_from_metadata(second_board_metadata, sct=sct)

                (
                    first_board_missing_stones,
                    new_missing_stones,
                ) = evaluate_state(first_board, second_board, all_pending)

                if previous_missing_stones != first_board_missing_stones:
                    print_describe_missing(
                        first_board_missing_stones,
                        first_board_metadata["name"],
                    )
                    previous_missing_stones = first_board_missing_stones

                if first_board_metadata["click"]:
                    if len(new_missing_stones) > 2:
                        continue

                    elif len(all_pending) > 0 or len(new_missing_stones) > 0:
                        all_pending, stones_to_play = update_all_pending(
                            all_pending,
                            first_board_missing_stones,
                            new_missing_stones,
                            delay,
                        )

                        up_next = play_stones(
                            first_board, stones_to_play, up_next, screen_scale
                        )

    except KeyboardInterrupt:
        exit_handler(first_board_metadata, second_board_metadata)


def run_app():
    welcome_message()
    available_boards = show_boards_list()

    first_board_metadata = get_board_name(available_boards, "first board")
    second_board_metadata = get_board_name(available_boards, "second board")

    first_board_metadata = update_handler(first_board_metadata)
    second_board_metadata = update_handler(second_board_metadata)

    watch_boards(first_board_metadata, second_board_metadata)


if __name__ == "__main__":
    run_app()
