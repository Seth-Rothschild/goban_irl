import cv2
import numpy as np

def find_width_and_height(start, end):
    """Given two points (x1, y1), (x2, y2)
    return (|x2-x1|, |y2-y1|)
    """
    width = int(abs(start[0] - end[0]))
    height = int(abs(start[1] - end[1]))

    return (width, height)

def crop(image, boundary):
    xmin, xmax, ymin, ymax = boundary
    """Does opencv crop but takes x arguments before y"""
    return image[int(ymin) : int(ymax), int(xmin) : int(xmax)]


def perspective_transform(image, corners):
    """Does opencv perspective transform with 4 corners as input)"""
    japan_board_ratio = 454.5 / 424.2
    topleft, topright, bottomleft, bottomright = corners
    width, _ = find_width_and_height(bottomright, bottomleft)
    _, height = find_width_and_height(topright, bottomright)
    source = np.array(corners, np.float32)
    destination = np.array(
        [(0, 0), (width, 0), (0, height), (width, height)], np.float32
    )
    M = cv2.getPerspectiveTransform(source, destination)
    transformed_subimage = cv2.warpPerspective(image, M, (width, height))
    board_subimage = scale_image(
        transformed_subimage,
        target_width=width,
        target_height=int(japan_board_ratio * width),
    )

    return board_subimage

def scale_image(image, target_width, target_height):
    """Does opencv resize to target width and target height"""
    return cv2.resize(image, (target_width, target_height))
