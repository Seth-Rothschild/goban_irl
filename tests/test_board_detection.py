import pytest
import cv2
import numpy as np
import os
from goban_irl.board import Board


def test_transform_image_two_corners():
    """If transform image is called with two corners
    Crop the image to the rectangle defined by the two corners
    """
    board = Board()
    image = "tests/image_samples/find_stones_test_1.png"
    corners = [(888, 248), (2470, 1830)]

    img = board.transform_image(image, corners)
    height, width, _ = img.shape
    assert height == corners[1][1] - corners[0][1]
    assert width == corners[1][0] - corners[0][0]


def test_transform_image_four_corners():
    """If transform image is called with four corners
    Run a perspective transform and resize to a standard board size based on the wider width
    """
    board = Board()
    image = "tests/image_samples/real_board_1.png"
    corners = [(590, 1328), (2232, 1330), (2669, 3059), (100, 3083)]

    img = board.transform_image(image, corners)
    height, width, _ = img.shape
    assert width == corners[2][0] - corners[3][0]
    assert height == int((454.5 / 424.2) * width)


def test_find_state_from_image():
    """Given an image pre-processed by transform_image
    Correctly identify black stones, white stones, and empty spaces
    Test images have white stones at [0][0], [15][3], black stones at [15][3] and [18][18]
    """

    def check_stones(board):
        for i, row in enumerate(board.state):
            for j, state in enumerate(row):
                loc = (i, j)
                if loc == (0, 0) or loc == (15, 3):
                    assert state == "white", loc
                elif loc == (18, 18) or loc == (3, 15):
                    assert state == "black", loc
                else:
                    assert state == "empty", loc

    corners = [(888, 248), (2470, 1830)]

    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_2.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_3.png", corners=corners)
    check_stones(board)

    corners = [(1105, 548), (2956, 559), (3669, 2305), (455, 2315)]
    board = Board(image="tests/image_samples/real_board_1.png", corners=corners)
    check_stones(board)

    corners = [(1129, 623), (2867, 654), (3349, 2469), (653, 2456)]
    board = Board(image="tests/image_samples/real_board_2.png", corners=corners)
    check_stones(board)


# def test_find_corners_helper():
#     images = ['real_board_1.png', 'real_board_2.png', 'real_board_3.png']
#     for path in images:
#         img = cv2.imread(path)

#         def click(event, x, y, flags, param):
#             if event == cv2.EVENT_LBUTTONDOWN:
#                 loc = (x, y)
#                 print('({}, {}),'.format(x, y))

#         cv2.namedWindow("image")
#         cv2.setMouseCallback("image", click)
#         cv2.imshow("image", img)
#         cv2.waitKey(0)
#         print('----')
#     assert False
