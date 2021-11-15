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

def check_bgr_blue(im):
    return im.mean(axis=0).mean(axis=0)[0]


def check_hsv_value(im):
    return cv2.cvtColor(im, cv2.COLOR_BGR2HSV).mean(axis=0).mean(axis=0)[2]


def check_bw(im):
    return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).mean(axis=0).mean(axis=0)


def check_bgr_and_bw(im):
    return check_bgr_blue(im) + check_bw(im)

def import_image(path):
    return cv2.imread(path)

def show_intersections(board_subimage, intersections):
    img = board_subimage
    for row in intersections:
        for loc in row:
            img = cv2.circle(img, loc, 10, (255, 0, 0))
    cv2.imshow("Proposed intersections", img)
    cv2.waitKey(0)
    destroy_all_windows()

def show_stones(board_subimage, stone_boundaries, state):
    img = board_subimage
    for i, row in enumerate(stone_boundaries):
        for j, (xmin, xmax, ymin, ymax) in enumerate(row):
            if state[i][j] == 'black':
                img = cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 0, 0), -1)
            elif state[i][j] == 'white':
                img = cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (255, 255, 255), -1)
            else:
                continue
    cv2.imshow("Stones detected", img)
    cv2.waitKey(0)
    destroy_all_windows()

def destroy_all_windows():
    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)
