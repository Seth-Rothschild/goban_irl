import itertools

import pytest
import cv2

from goban_irl.board import Board


def test_transform_image_two_corners():
    """If transform image is called with two corners
    Crop the image to the rectangle defined by the two corners
    """

    image = "tests/image_samples/find_stones_test_1.png"
    corners = [(888, 248), (2470, 1830)]
    board = Board(image, corners)

    cv2image = cv2.imread(image)
    img = board.transform_image(cv2image, corners)
    height, width, _ = img.shape
    assert height == corners[1][1] - corners[0][1]
    assert width == corners[1][0] - corners[0][0]


def test_transform_image_four_corners():
    """If transform image is called with four corners
    Run a perspective transform and resize to a standard board size based on the wider width
    """

    image = "tests/image_samples/real_board_1.png"
    corners = [(590, 1328), (2232, 1330), (2669, 3059), (100, 3083)]
    board = Board(image, corners)

    cv2image = cv2.imread(image)
    img = board.transform_image(cv2image, corners)
    height, width, _ = img.shape
    assert width == corners[2][0] - corners[3][0]
    assert height == int((454.5 / 424.2) * width)


def test_find_state_from_rectangular():
    """Given an image with two corners
    Correctly identify black stones, white stones, and empty spaces
    """

    corners = [(888, 248), (2470, 1830)]

    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_2.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_3.png", corners=corners)
    check_stones(board)


def test_find_state_opposite_corners():
    """Given an image with bottomleft and topright specified instead of topleft, bottomright
    Correctly identify black stones, white stones, and empty spaces
    """
    corners = [(888, 1830), (2470, 248)]

    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_2.png", corners=corners)
    check_stones(board)

    board = Board(image="tests/image_samples/find_stones_test_3.png", corners=corners)
    check_stones(board)


def test_find_state_from_trapezoid():
    """GIven an image with four corners
    Correctly identify black stones, white stones, and empty spaces
    """
    corners = [(1105, 548), (2956, 559), (3669, 2305), (455, 2315)]
    board = Board(image="tests/image_samples/real_board_1.png", corners=corners)
    check_stones(board)

    corners = [(1129, 623), (2867, 654), (3349, 2469), (653, 2456)]
    board = Board(image="tests/image_samples/real_board_2.png", corners=corners)
    check_stones(board)


def test_reorder_corners():
    """Given four corners rearrange to topleft, topright, bottomleft, bottomright
    Given two corners rearrange so that the one with the minimum sum is first
    """
    topleft = (1, 1)
    topright = (4, 2)
    bottomleft = (0, 5)
    bottomright = (6, 6)

    board = Board()
    corners = [topleft, topright, bottomleft, bottomright]
    permutations = list(itertools.permutations(corners))
    for permutation in permutations:
        assert board._sort_corners(permutation) == corners

    corners = [topleft, bottomright]
    assert board._sort_corners(corners[::-1]) == corners


def test_flip():
    """If board is given the flip argument then reverse the order of state.
    This handles the common use case where the camera is opposite the player
    """
    corners = [(888, 1830), (2470, 248)]
    board = Board(
        image="tests/image_samples/find_stones_test_1.png", corners=corners, flip=True
    )

    assert board.state[18][18] == "white"
    assert board.state[0][0] == "black"


def check_stones(board):
    """Helper function to test images have white stones at [0][0], [15][3], black stones at [15][3] and [18][18]
    Assert those are correct and everything else is empty
    """
    for i, row in enumerate(board.state):
        for j, state in enumerate(row):
            loc = (i, j)
            if loc == (0, 0) or loc == (15, 3):
                assert state == "white", loc
            elif loc == (18, 18) or loc == (3, 15):
                assert state == "black", loc
            else:
                assert state == "empty", loc


def test_calibrate():
    corners = [(888, 1830), (2470, 248)]
    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    board.calibrate(
        black_stones=[(18, 18), (3, 15)],
        white_stones=[(0, 0), (15, 3)],
        empty_spaces=[(1, 1), (17, 17), (1, 17), (17, 1)],
    )

    board = Board(image="tests/image_samples/find_stones_test_2.png", corners=corners)
    board.calibrate(
        black_stones=[(18, 18), (3, 15)],
        white_stones=[(0, 0), (15, 3)],
        empty_spaces=[(1, 1), (17, 17), (1, 17), (17, 1)],
    )

    board = Board(image="tests/image_samples/find_stones_test_3.png", corners=corners)
    board.calibrate(
        black_stones=[(18, 18), (3, 15)],
        white_stones=[(0, 0), (15, 3)],
        empty_spaces=[(1, 1), (17, 17), (1, 17), (17, 1)],
    )

    corners = [(1105, 548), (2956, 559), (3669, 2305), (455, 2315)]
    board = Board(image="tests/image_samples/real_board_1.png", corners=corners)
    board.calibrate(
        black_stones=[(18, 18), (3, 15)],
        white_stones=[(0, 0), (15, 3)],
        empty_spaces=[(1, 1), (17, 17), (1, 17), (17, 1)],
    )


def test_calibrate_edges(capsys):
    corners = [(888, 1830), (2470, 248)]
    board = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    with pytest.raises(ValueError):
        board.calibrate()

    with pytest.raises(ValueError):
        board.calibrate(
            black_stones=[(3, 15)],
            white_stones=[(0, 0), (15, 3)],
            empty_spaces=[(1, 1), (17, 17), (1, 17), (18, 18)],
            verbose=True,
        )

    board.calibrate(
        black_stones=[(18, 18), (3, 15)],
        white_stones=[(0, 0), (15, 3)],
        empty_spaces=[(1, 1), (17, 17), (1, 17), (17, 1)],
        verbose=True,
    )
    captured = capsys.readouterr()
    assert "check_bgr_and_bw partitions with gaps of size" in captured.out


def test_human_readable():
    board = Board()
    loc = (0, 0)
    assert board._human_readable_numeric(loc) == "1-19"
    assert board._human_readable_alpha(loc) == "A19"

    loc = (18, 0)
    assert board._human_readable_numeric(loc) == "1-1"
    assert board._human_readable_alpha(loc) == "A1"

    loc = (0, 18)
    assert board._human_readable_numeric(loc) == "19-19"
    assert board._human_readable_alpha(loc) == "T19"

    loc = (18, 18)
    assert board._human_readable_numeric(loc) == "19-1"
    assert board._human_readable_alpha(loc) == "T1"


def test_compare_to():
    corners = [(888, 1830), (2470, 248)]
    board_1 = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)
    board_2 = Board(image="tests/image_samples/find_stones_test_1.png", corners=corners)

    assert board_1.compare_to(board_2) == []

    board_1.state[1][1] = "black"

    assert board_1.compare_to(board_2) == [(1, 1, "black", "empty")]
    assert board_2.compare_to(board_1) == [(1, 1, "empty", "black")]

    board_2.state[17][17] = "white"

    assert (17, 17, "empty", "white") in board_1.compare_to(board_2)
    assert (17, 17, "white", "empty") in board_2.compare_to(board_1)

    assert len(board_2.compare_to(board_1)) == 2
