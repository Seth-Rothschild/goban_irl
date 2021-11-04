import cv2
import numpy as np


class Board:
    def __init__(self, corners=[], image=None):
        if image:
            transformed_image = self.transform_image(image, corners)
            self.find_state_from_image(transformed_image)

    def transform_image(self, image, corners):
        """Given corner locations, either crop or perspective warp an image
        Assumptions:
            Rectangular images will have the top left and bottom right corner
            When corners form a trapezoid, assume bases are horizontal and bottom is longer than top

        """
        image = cv2.imread(image)
        if len(corners) == 2:
            width, height = _find_width_and_height(corners[0], corners[1])
            transformed_image = image[
                corners[0][1] : corners[0][1] + height,
                corners[0][0] : corners[0][0] + width,
            ]
        elif len(corners) == 4:
            width, _ = _find_width_and_height(corners[3], corners[2])
            _, height = _find_width_and_height(corners[1], corners[2])
            japan_board_ratio = 454.5 / 424.2

            source = np.array(corners, np.float32)
            destination = np.array(
                [(0, 0), (width, 0), (width, height), (0, height)], np.float32
            )
            M = cv2.getPerspectiveTransform(source, destination)
            transformed_image = cv2.warpPerspective(image, M, (width, height))
            transformed_image = cv2.resize(
                transformed_image, (width, int(japan_board_ratio * width))
            )

        return transformed_image

    def find_state_from_image(self, board_subimage, debug=False):
        """Compute the average color of a rectangle around each intersection
        Claim that colors with more blue are white stones, less blue are black stones
        This works better and faster than it has any right to.
        """
        height, width, _ = board_subimage.shape
        xstep = width / 18
        ystep = height / 18

        x_locs = [round((ind * xstep)) for ind in range(19)]
        y_locs = [round((ind * ystep)) for ind in range(19)]

        intersections = []
        for y_loc in y_locs:
            intersections.append([(x_loc, y_loc) for x_loc in x_locs])

        if debug:
            img = board_subimage
            for row in intersections:
                for loc in row:
                    img = cv2.circle(img, loc, 10, (255, 0, 0))

                self.intersections = intersections
                self.averages = [[0 for _ in range(19)] for _ in range(19)]
            cv2.imshow("image", img)
            cv2.waitKey(0)

        self.state = [["empty" for _ in range(19)] for _ in range(19)]
        for i, row in enumerate(intersections):
            for j, loc in enumerate(row):
                xmin, ymin = (
                    max(0, int(loc[0] - xstep / 2)),
                    max(0, int(loc[1] - ystep / 2)),
                )
                xmax, ymax = (
                    int(min(loc[0] + xstep // 2, width)),
                    int(min(loc[1] + ystep // 2, height)),
                )
                stone_subimage = board_subimage[ymin:ymax, xmin:xmax]

                average = stone_subimage.mean(axis=0).mean(axis=0)
                subimage_blue_mean = average[0]

                if debug:
                    self.averages[i][j] = average

                if subimage_blue_mean > 140:
                    position_state = "white"
                elif subimage_blue_mean < 72:
                    position_state = "black"
                else:
                    position_state = "empty"
                self.state[i][j] = position_state


def _find_width_and_height(start, end):
    """Given two points (x1, y1), (x2, y2)
    return (|x2-x1|, |y2-y1|)
    """
    width = int(abs(start[0] - end[0]))
    height = int(abs(start[1] - end[1]))

    return (width, height)
