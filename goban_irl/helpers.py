import pyautogui
import goban_irl.opencv_utilities as utils

from goban_irl.board import Board

def boxify(string):
    horizontal_line = (len(string) + 4) * "-"
    return "+{}+\n|  {}  |\n+{}+\n\n".format(horizontal_line, string, horizontal_line)


def prompt_handler(prompt):
    true_options = ["y", "Y", "yes", "Yes", ""]
    false_options = ["n", "N", "no", "No"]
    response = input("{}: ".format(prompt))
    if response in true_options:
        return True
    elif response in false_options:
        return False
    else:
        print("Please input either {} or {}".format(true_options[0], false_options[0]))
        return prompt_handler(prompt)


def get_scale():
    img = utils.get_snapshot("virtual")
    height, width, _ = img.shape
    return height / pyautogui.size().height


def get_nearest_intersection(xstep, ystep, click):
    return (round(click[1] / ystep), round(click[0] / xstep))


def click(board, missing_stone_location, screen_scale=2):
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


def print_describe_missing(missing_stones, board_name):
    print("")
    if len(missing_stones) == 0:
        print('Board {} is not missing any stones'.format(board_name))
        return

    board = Board()

    if len(missing_stones) > 0:
        if len(missing_stones) > 5:
            print(
                "Board {} is missing many stones ({})".format(
                    board_name, len(missing_stones)
                )
            )
        else:
            print("There are missing stones:")
            for (i, j, this_stone, other_stone) in missing_stones:
                print(
                    "    At {} ({}) {} has {} and other board has {}".format(
                        board._human_readable_alpha((i, j)),
                        board._human_readable_numeric((i, j)),
                        board_name,
                        this_stone,
                        other_stone,
                    )
                )
        return
