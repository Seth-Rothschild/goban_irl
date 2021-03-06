import cv2
import mss
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
    return cv2.cvtColor(im.copy(), cv2.COLOR_BGR2HSV).mean(axis=0).mean(axis=0)[2]


def check_bw(im):
    return cv2.cvtColor(im.copy(), cv2.COLOR_BGR2GRAY).mean(axis=0).mean(axis=0)


def check_bgr_subimage(im):
    height, width, _ = im.shape
    im = crop(
        im.copy(), (2 * width // 5, 4 * width // 5, 2 * height // 5, 4 * height // 5)
    )
    return check_bgr_blue(im)


def check_bw_subimage(im):
    height, width, _ = im.shape
    im = crop(
        im.copy(), (2 * width // 5, 4 * width // 5, 2 * height // 5, 4 * height // 5)
    )
    return check_bw(im)


def check_subimage_max_difference(im):
    height, width, _ = im.shape
    im = crop(
        im.copy(), (2 * width // 5, 4 * width // 5, 2 * height // 5, 4 * height // 5)
    )
    return check_max_difference(im)


def check_sum(im):
    average = im.copy().mean(axis=0).mean(axis=0)
    return sum(average)


def check_max_difference(im):
    average = im.mean(axis=0).mean(axis=0)
    max_difference = max(
        [
            abs(average[1] - average[0]),
            abs(average[2] - average[0]),
            abs(average[1] - average[0]),
        ]
    )
    if max_difference < 70:
        score = check_sum(im)
        if score > 700:
            return 800
        else:
            return 600
    else:
        return 700


def check_bgr_and_bw(im):
    return check_bgr_blue(im) + check_bw(im)


def import_image(path):
    return cv2.imread(path)


def video_capture():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise IOError("Cannot open webcam")
    _, frame = cap.read()
    return frame


def destroy_all_windows():
    cv2.waitKey(1)
    cv2.destroyAllWindows()
    cv2.waitKey(1)


def show_intersections(board_subimage, intersections):
    img = board_subimage.copy()
    for row in intersections:
        for loc in row:
            img = cv2.circle(img, loc, 10, (255, 0, 0))
    cv2.imshow("Proposed intersections", img)
    cv2.waitKey(0)
    destroy_all_windows()


def show_stones(board_subimage, stone_boundaries, state):
    img = board_subimage.copy()
    for i, row in enumerate(stone_boundaries):
        for j, (xmin, xmax, ymin, ymax) in enumerate(row):
            if state[i][j] == "black":
                img = cv2.rectangle(img, (xmin, ymin), (xmax, ymax), (0, 0, 0), -1)
            elif state[i][j] == "white":
                img = cv2.rectangle(
                    img, (xmin, ymin), (xmax, ymax), (255, 255, 255), -1
                )
            else:
                continue
    cv2.imshow("Stones detected", img)
    cv2.waitKey(0)
    destroy_all_windows()


def get_clicks(img):
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
    destroy_all_windows()

    return [(int(x * 1.5), int(y * 1.5)) for (x, y) in intersections]


DETECTION_FUNCTIONS = [
    check_bgr_blue,
    check_hsv_value,
    check_bw,
    check_bgr_subimage,
    check_bw_subimage,
    check_subimage_max_difference,
    check_sum,
    check_max_difference,
    check_bgr_and_bw,
]


def load_detection_function(function_name):
    for function in DETECTION_FUNCTIONS:
        if function_name == function.__name__:
            return function
    raise ValueError("Detection function {} not loaded".format(function_name))


def get_snapshot(loader_type, sct=None):
    if loader_type == "virtual":
        if sct is None:
            with mss.mss() as sct:
                img = np.array(sct.grab(sct.monitors[1]))
        else:
            img = np.array(sct.grab(sct.monitors[1]))
        height, width, _ = img.shape

    elif loader_type == "physical":
        img = video_capture()

    return img
