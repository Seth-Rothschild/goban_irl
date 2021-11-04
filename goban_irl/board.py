import cv2
import numpy as np


class Board:
    def __init__(self, corners=[], image=None, flip=False, debug=False):
        if image:
            transformed_image = self.transform_image(image, corners)
            self.find_state_from_image(transformed_image, debug=debug)

            if flip:
                self.state = self.state[::-1]


    def transform_image(self, image, corners):
        """Given corner locations, either crop or perspective warp an image
        Assumptions:
            Rectangular images will have the top left and bottom right corner
            When corners form a trapezoid, assume bases are horizontal and bottom is longer than top

        """
        image = cv2.imread(image)
        if len(corners) == 2:
            self.corners = self._sort_corners(corners)
            (xmin, ymin), (xmax, ymax) = self.corners
            
            transformed_image = crop(image, xmin, xmax, ymin, ymax)
            
        elif len(corners) == 4:
            self.corners = self._sort_corners(corners)
            topleft, topright, bottomleft, bottomright = self.corners
            width, _ = _find_width_and_height(bottomright, bottomleft)
            _, height = _find_width_and_height(topright, bottomright)
            japan_board_ratio = 454.5 / 424.2

            source = np.array(self.corners, np.float32)
            destination = np.array(
                [(0, 0), (width, 0), (0, height), (width, height)], np.float32
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

        intersections = self._get_intersections(board_subimage)
        stone_subimage_boundaries = self._get_stone_subimage_boundaries(
            board_subimage, intersections
        )

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

        for i, row in enumerate(stone_subimage_boundaries):
            for j, (xmin, xmax, ymin, ymax) in enumerate(row):
                stone_subimage = crop(board_subimage, xmin, xmax, ymin, ymax)
                position_state, average = self._detect_stone(stone_subimage)

                if debug:
                    self.averages[i][j] = average

                self.state[i][j] = position_state

    def compare(self, board2):
        """Compare this board state with another board
        returns:
            status (string 'ahead', 'behind', 'equal', 'mismatch'): Says how this board compares
            stones to play (list tuples (stone, loc))
        """

    def _get_intersections(self, image):
        """Generate a 19x19 array of (x, y) corresponding to the intersections"""
        _, _, xstep, ystep = get_board_params(image)

        x_locs = [round((ind * xstep)) for ind in range(19)]
        y_locs = [round((ind * ystep)) for ind in range(19)]

        intersections = [[(x_loc, y_loc) for x_loc in x_locs] for y_loc in y_locs]

        return intersections

    def _get_stone_subimage_boundaries(self, image, intersections):
        """Partition the board into stone regions by taking
        plus/minus xstep/2 and ystep/2 from the intersection. Notice
        that we need to be careful around the image edge because 
        negative indices have meaning.


        returns xmin, xmax, ymin, ymax
        """
        width, height, xstep, ystep = get_board_params(image)
        boundaries = [[0 for _ in range(19)] for _ in range(19)]
        for i, row in enumerate(intersections):
            for j, loc in enumerate(row):
                xmin, ymin = (
                    max(0, int(loc[0] - xstep / 2)),
                    max(0, int(loc[1] - ystep / 2)),
                )
                xmax, ymax = (
                    int(min(loc[0] + xstep / 2, width)),
                    int(min(loc[1] + ystep / 2, height)),
                )
                boundaries[i][j] = xmin, xmax, ymin, ymax
        return boundaries

    def _detect_stone(self, stone_subimage):
        """Takes in a stone subimage
        Decides whether that position is empty, black, or white.

        This particular implementation is stupid-but-effective since
        we just determine the amount of blue in the image on average.
        """
        average = stone_subimage.mean(axis=0).mean(axis=0)
        subimage_blue_mean = average[0]

        if subimage_blue_mean > 140:
            position_state = "white"
        elif subimage_blue_mean < 72:
            position_state = "black"
        else:
            position_state = "empty"

        return position_state, average

    def _sort_corners(self, corners):


        if len(corners) == 2:
            xmin, xmax = sorted([corner[0] for corner in corners])
            ymin, ymax = sorted([corner[1] for corner in corners])
            sorted_corners = [(xmin, ymin), (xmax, ymax)]
        
        if len(corners) == 4:
            sums = [sum(corner) for corner in corners]
            topleft_index = sums.index(min(sums))
            topleft = corners[topleft_index]

            bottomright_index = sums.index(max(sums))
            bottomright = corners[bottomright_index]
            remaining_corners = [
                corner
                for corner in corners
                if (corner != topleft) and (corner != bottomright)
            ]
            if remaining_corners[0][0] > remaining_corners[1][0]:
                topright, bottomleft = remaining_corners
            else:
                bottomleft, topright = remaining_corners
            sorted_corners = [topleft, topright, bottomleft, bottomright]
        return sorted_corners


def _find_width_and_height(start, end):
    """Given two points (x1, y1), (x2, y2)
    return (|x2-x1|, |y2-y1|)
    """
    width = int(abs(start[0] - end[0]))
    height = int(abs(start[1] - end[1]))

    return (width, height)


def get_board_params(image):
    height, width, _ = image.shape
    return width, height, width / 18, height / 18

def crop(image, xmin, xmax, ymin, ymax):
    """Does opencv crop but takes x arguments before y
    """
    return image[ymin:ymax, xmin:xmax]
