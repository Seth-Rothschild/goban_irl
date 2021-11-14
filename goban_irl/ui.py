import time
import json
import os
import itertools

import pyautogui
import cv2
import numpy as np

from goban_irl.board import Board
from goban_irl.utilities import check_bgr_and_bw


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


def _print_loaded_boards(boards_metadata):
    loaded_boards_message = ""
    if boards_metadata is None:
        loaded_boards_message += "You have not created any boards yet."
    else:
        for i, board in enumerate(boards_metadata):
            loaded_boards_message += "Board {}:\n   loader = {},\n    corners = {},\n    boundaries = {}\n\n".format(
                i, board['loader_type'], board['corners'], board['cutoffs']
            )


def _print_cornerloader_text(board_metadata):
    if board_metadata["loader_type"] == "virtual":
        print("Now, select two opposite corners of the board (e.g. (1, 1) and (19, 19)")
        print("Selected poitns will appear as red circles once they are clicked.")
        print("Once you've chosen two corners, you can exit the selector with q.")

    elif board_metadata["loader_type"] == "physical":
        print("Now, select FOUR corners of the board")
        print("Selected points will appear as red circles once they are clicked.")
        print("Once you've chosen four corners, you can exit the selector with q.")


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


def run_app():
    t0 = time.time()
    _print_welcome_message()

    if os.path.exists("virtual.json"):
        with open("virtual.json") as f:
            virtual_board_metadata = json.load(f)
    else:
        virtual_board_metadata = {"loader_type": "virtual"}
        virtual_board_metadata["corners"] = load_corners(virtual_board_metadata)

        virtual_board_metadata["cutoffs"] = (204, 316)
        virtual_board_metadata["flip"] = False
        with open("virtual.json", "w") as f:
            json.dump(virtual_board_metadata, f)

    if os.path.exists("physical.json"):
        with open("physical.json") as f:
            physical_board_metadata = json.load(f)

    else:
        physical_board_metadata = {"loader_type": "physical"}
        physical_board_metadata["corners"] = load_corners(physical_board_metadata)
        _, cutoffs = calibrate(physical_board_metadata)
        physical_board_metadata["cutoffs"] = cutoffs
        physical_board_metadata["flip"] = True
        with open("physical.json", "w") as f:
            json.dump(physical_board_metadata, f)

    _print_loaded_boards([virtual_board_metadata, physical_board_metadata])

    # v_corners = [(1755, 1608), (2904, 462)]
    # p_corners = [(1638, 909), (339, 904), (546, 49), (1390, 58)]

    i = 0
    while True:
        virtual_board = Board(
            image=ImageLoader(virtual_board_metadata["loader_type"]).snapshot(),
            corners=virtual_board_metadata["corners"],
            detection_function=check_bgr_and_bw,
            cutoffs=virtual_board_metadata["cutoffs"],
            flip=virtual_board_metadata["flip"],
        )
        physical_board = Board(
            image=ImageLoader(physical_board_metadata["loader_type"]).snapshot(),
            corners=physical_board_metadata["corners"],
            detection_function=check_bgr_and_bw,
            cutoffs=physical_board_metadata["cutoffs"],
            flip=physical_board_metadata["flip"],
        )

        missing_stones_on_virtual = virtual_board.compare_to(physical_board)
        missing_stones_on_physical = physical_board.compare_to(virtual_board)

        if len(missing_stones_on_physical) > 0:
            print("Physical board is missing some stones:")
            if len(missing_stones_on_physical) > 5:
                print(
                    "    Missing many stones ({})".format(
                        len(missing_stones_on_physical)
                    )
                )
            else:
                for (row, col) in missing_stones_on_physical:
                    print(
                        "    Missing {} stone at {} ({})".format(
                            virtual_board.state[row][col],
                            virtual_board._human_readable_alpha((row, col)),
                            virtual_board._human_readable_numeric((row,col)),
                        )
                    )
        print('')
        if len(missing_stones_on_virtual) > 0:
            print("Virtual board is missing some stones:")
            if len(missing_stones_on_virtual) > 5:
                print(
                    "    Missing many stones ({})".format(
                        len(missing_stones_on_virtual)
                    )
                )
            else:
                for (row, col) in missing_stones_on_virtual:
                    print(
                        "    Missing {} stone at {} ({})".format(
                            physical_board.state[row][col],
                            physical_board._human_readable_alpha((row, col)),
                            physical_board._human_readable_numeric((row,col)),
                        )
                    )

        if len(missing_stones_on_virtual) == 1 and len(missing_stones_on_physical)==0:
            loc_x, loc_y = missing_stones_on_virtual[0]
            int_x, int_y = virtual_board.intersections[loc_x][loc_y]
            topleft_x, topleft_y = virtual_board.corners[0]
            click_loc = ((topleft_x + int_x) // 2, (topleft_y + int_y) // 2)
            pyautogui.moveTo(click_loc[0], click_loc[1], .25, pyautogui.easeInBounce)
            pyautogui.click()
            #pyautogui.click(click_loc[0], click_loc[1])
        time.sleep(1)
        i += 1
        print("iteration {}".format(i))


def _boxify(string):
    """Takes a string and returns a nice ascii box"""
    horizontal_line = (len(string) + 4) * "-"
    return "+{}+\n|  {}  |\n+{}+\n\n".format(horizontal_line, string, horizontal_line)


def get_corners(img):
    title = "corners (press q when done)"
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
    return board.calibrate(
        black_stones=black_stones, white_stones=white_stones, empty_spaces=empty_spaces
    )
    

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
            return frame


if __name__ == "__main__":
    run_app()
    # import itertools
    # p_loader = ImageLoader(board_type="physical")
    # p_corners = load_physical_board(p_loader)
    # print("p_corners = {}".format(p_corners))
    # #p_corners = [(349, 916), (549, 63), (1377, 78), (1630, 912)]
    # #p_corners = [(1536, 925), (304, 934), (546, 390), (1251, 396)]

    # board = Board(p_loader.snapshot(), p_corners, debug=True)
    # black_stones = [(17, 17), (1, 1), (1, 17), (17, 1)]
    # white_stones = [(18, 18), (0, 0), (18, 0), (0, 18)]
    # empty_spaces = [x for x in set(list(itertools.combinations(list(range(19)) + list(range(19)), 2))) if ((x not in white_stones) and (x not in black_stones))]
    # function, cutoffs = board.calibrate(black_stones=black_stones, white_stones=white_stones, empty_spaces=empty_spaces)
    # print(function,
    #      cutoffs)
