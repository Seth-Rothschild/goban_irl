import cv2
import numpy as np
from goban_irl.utilities import crop, perspective_transform

class Board:
    def __init__(
        self,
        image=None,
        corners=[],
        detect_type="yellow",
        cutoffs=(70, 150),
        flip=False,
        debug=False,
    ):
        """Create a digital representation of a go board from an image

        Args:
            image (str): The path to the image of the board. If image is None, initialize an empty board object.
            corners (list[tuple[int, int]]): A list of (x, y) pairs for the corners of the board. Given two corners, crop the image to the rectangle those corners define. Given four corners, do an opencv perspective transform to make a rectangle.
            detect_type (str, default `'yellow'`): The type of stone detection to do.
            cutoffs (tuple[int, int]): Values to partition between black, empty, and white.
            flip (bool): Whether or not to flip the board. This is useful when the camera is opposite the person.
            debug (bool): Enables debug mode which shows detected corners, detected stones.

        """
        if image is not None:
            if isinstance(image, str):
                image = cv2.imread(image)

            self.corners = self._sort_corners(corners)

            board_subimage = self.transform_image(image, self.corners)
            self.find_state_from_image(
                board_subimage, detect_type=detect_type, cutoffs=cutoffs, debug=debug
            )

            if flip:
                self.state = self.state[::-1]

    def transform_image(self, image, corners):
        """Create a rectangular board from an opencv image and corner locations.

        Args:
            image (opencv image): An opencv image a go board
            corners (list[tuple[int, int]]): A list of (x, y) pairs for the corners of the board. Given two corners, crop the image to a rectangle those corners define. Given four corners, do an opencv perspective transform to get a rectangle.

        returns:
            board_subimage (opencv image): A rectangular image whose corners are the (1, 1) and (19, 19) points on the board.

        """
        if len(corners) == 2:
            (xmin, ymin), (xmax, ymax) = self.corners
            board_subimage = crop(image, xmin, xmax, ymin, ymax)

        elif len(corners) == 4:
            board_subimage = perspective_transform(image, corners)
        return board_subimage

    def find_state_from_image(
        self, board_subimage, debug=False, detect_type=None, cutoffs=None
    ):
        """Create a 19x19 array `state` filled with `empty`, `black` and `white`

        Args:
            board_subimage (opencv image): A rectangular image whose corners are the (1, 1) and (19, 19) points on the board.
            debug (bool, default False): Enables debug mode which shows detected corners, detected stones.

        returns:
            self.state: A 19x19 array of `empty`, `black`, and `white` corresponding to the image and detection function
        """

        self.intersections = self._get_intersections(board_subimage)
        stone_subimage_boundaries = self._get_stone_subimage_boundaries(
            board_subimage, self.intersections
        )

        # if debug:
        #     img = board_subimage
        #     for row in intersections:
        #         for loc in row:
        #             img = cv2.circle(img, loc, 10, (255, 0, 0))

        #         self.averages = [[0 for _ in range(19)] for _ in range(19)]
        #     cv2.imshow("image", img)
        # cv2.waitKey(0)

        self.state = [["empty" for _ in range(19)] for _ in range(19)]

        for i, row in enumerate(stone_subimage_boundaries):
            for j, (xmin, xmax, ymin, ymax) in enumerate(row):
                stone_subimage = crop(board_subimage, xmin, xmax, ymin, ymax)
                position_state, average = self.detect_stone(
                    stone_subimage, detect_type=detect_type, cutoffs=cutoffs
                )

                # if debug:
                #     self.averages[i][j] = average

                self.state[i][j] = position_state

    def detect_stone(self, stone_subimage, detect_type=None, cutoffs=None):
        """Run various stone detection functions based on a stone subimage

        Args:
            stone_subimage (opencv image): Maximal image around a stone.
            detect_type (str): Type of stone detection to do
            cutoffs (tuple[int, int]): Values to distinguish between black, empty, and white

        returns:
            position_state (str): Either `'black'`, `'empty'`, or `'white'`
            deciding_value (float): The value used to make the decision
        """
        if detect_type == "yellow":
            deciding_value = stone_subimage.mean(axis=0).mean(axis=0)[0]
            position_state = self._find_region(deciding_value, cutoffs)

        return position_state, deciding_value

    def compare_to(self, board2):
        """Compare this board state with another board
        returns:
            missing_stones (list(tuple(int, int))): Indices where board2 is missing stones of board1
        """
        missing_stones = []
        for i, row in enumerate(self.state):
            for j, value in enumerate(row):
                other_value = board2.state[i][j]
                if value == "empty" and (
                    other_value == "black" or other_value == "white"
                ):
                    missing_stones.append((i, j))
        return missing_stones

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

    def _find_region(self, deciding_value, cutoffs):
        min_cutoff, max_cutoff = cutoffs
        if deciding_value < min_cutoff:
            position_state = "black"
        elif deciding_value > max_cutoff:
            position_state = "white"
        else:
            position_state = "empty"
        return position_state


def get_board_params(image):
    height, width, _ = image.shape
    return width, height, width / 18, height / 18


