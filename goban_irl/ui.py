import time

import pyautogui
import cv2
import numpy as np

from goban_irl.board import Board


def _boxify(string):
    """Takes a string and returns a nice ascii box"""
    horizontal_line = (len(string) + 4) * "-"
    return "+{}+\n|  {}  |\n+{}+\n\n".format(horizontal_line, string, horizontal_line)

def run_app():
    t0 = time.time()
    print(_boxify("Welcome!"))

    print(
        "This application helps you set up virtual and physical boards to be read by goban_irl."
    )
    print(
        "Optionally, we can also autoplay stones on the virtual board when stones are played on a physical board\n\n"
    )


    v_loader = ImageLoader(board_type="virtual")
    #v_corners = load_virtual_board(v_loader)
    p_loader = ImageLoader(board_type="physical")
    #p_corners = load_physical_board(p_loader)
    v_corners = [(1755, 1608), (2904, 462)]
    p_corners = [(1536, 925), (304, 934), (546, 390), (1251, 396)]
    print('v_corners', v_corners)
    print('p_corner', p_corners)

    while True:
        i = 0
        v_board = Board(image=v_loader.snapshot(), corners=v_corners)
        p_board = Board(image=p_loader.snapshot(), corners=p_corners, flip=True, debug=True)
        v_board_missing = v_board.compare_to(p_board)
        p_board_missing = p_board.compare_to(v_board)
        print('p_board 0 0', p_board.averages[0][0])
        print('p_board 0 18', p_board.averages[0][18])
        print('p_board 18 0', p_board.averages[18][0])
        print('p_board 18 18', p_board.averages[18][18])

        print('p_board 3 3', p_board.averages[3][3])
        print('p_board 15 15', p_board.averages[-3][-3])
        print('p_board 3 15', p_board.averages[3][15])
        print('p_board 15 13', p_board.averages[15][3])


        print('vboard missing', v_board_missing)
        print('pboard missing', p_board_missing)
        if len(v_board_missing)==1:
            loc_x, loc_y = v_board_missing[0]
            int_x, int_y = v_board.intersections[loc_x][loc_y]
            #topleft_x, topleft_y = v_board.corners[0]
            topleft_x, topleft_y = (1755, 462)
            print(topleft_x, topleft_y)
            print(int_x, int_y)
            click_loc = ((topleft_x + int_x)//2, (topleft_y + int_y)//2)
            pyautogui.click(click_loc[0], click_loc[1])
        time.sleep(10)
        i += 1
        print('iteration {}'.format(i))

    


def load_virtual_board(loader):
    print("Now, select two opposite corners of the board (e.g. (1, 1) and (19, 19)")
    print("Selected poitns will appear as red circles once they are clicked.")
    print("Once you've chosen two corners, you can exit the selector with q.")
    input("\nMake your board visible on screen and press enter to continue...")
    corners = []
    img = loader.snapshot()
    while len(corners) != 2:
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        img = loader.snapshot()
        corners = get_corners(img)
    

    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    print("\nWe have circled the proposed intersections")
    board = Board(corners=corners, image=loader.snapshot(), debug=True)

    return corners

def load_physical_board(loader):
    print("Now, select FOUR corners of the board")
    print("Selected points will appear as red circles once they are clicked.")
    print("Once you've chosen four corners, you can exit the selector with q.")
    input("\nMake sure your webcam is mounted and pointed at your board and press enter to continue...")
    corners = []
    img = loader.snapshot()
    while len(corners) != 4:
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        img = loader.snapshot()
        corners = get_corners(img)
    

    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)
    print("\nWe have circled the proposed intersections")
    board = Board(corners=corners, image=loader.snapshot(), debug=True)

    return corners

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


def prompt_handler(prompt, true_options, false_options):
    """Allows for multiple responses to a prompt and returns a bool.
    Also adds newline at beginning and colon at end.

    Args:
        prompt (string): The words to appear on the input line
        true_options (list[str]): The options that should return True
        false_options (list[str]): The options that should return False
    """
    response = input("/n{}: ".format(prompt))
    if response in true_options:
        return True
    elif response in false_options:
        return False
    else:
        print("Please input either {} or {}".format(true_options[0], false_options[0]))
        prompt_handler(prompt, true_options, false_options)


if __name__ == "__main__":
    run_app()
