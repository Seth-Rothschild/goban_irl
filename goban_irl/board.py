import goban_irl.utilities as utils


class Board:
    def __init__(
        self,
        image=None,
        corners=[],
        detection_function=None,
        cutoffs=None,
        flip=False,
        debug=False,
    ):
        """Create a digital representation of a go board from an image

        Args:
            image (str): The path to the image of the board. If image is None, initialize an empty board object.
            corners (list[tuple[int, int]]): A list of (x, y) pairs for the corners of the board. Given two corners, crop the image to the rectangle those corners define. Given four corners, do an opencv perspective transform to make a rectangle.
            detection_function (function: opencv image -> int): The type of stone detection to do.
            cutoffs (tuple[int, int]): Values to partition between black, empty, and white.
            flip (bool): Whether or not to flip the board. This is useful when the camera is opposite the person.
            debug (bool): Enables debug mode which shows detected corners, detected stones.

        Attributes:
            corners (list[tuple[int, int]]): The sorted corners which define a board_subimage.
            board_subimage (opencv image): An opencv image whose corners are the playable corners of the board.
            intersections: A 19x19 array of intersections on the board_subimage.
            stone_subimage_boundaries: A 19x19 array defining the x and y mins and maxes for a stone subimage.
            state: A 19x19 array whose entries are white, black, or empty.


        Example:
            from goban_irl import check_bgr_and_bw

            board_1 = Board(image='/path/to/image.png', corners=[(400, 1000), (1200, 1900)]

            board_2_corners = [(1437, 679), (2364, 679), (1437, 1617), (2364, 1617)]
            board_2 = Board(
                image='/path/to/other/image.png',
                corners=board_2_corners,
                detection_function=check_bgr_and_bw,
                cutoffs=(204, 316)
            )

        """
        if image is not None:
            if isinstance(image, str):
                image = utils.import_image(image)

            self.corners = self._sort_corners(corners)

            self.board_subimage = self.transform_image(image, self.corners)

            self.intersections = self.get_intersections(self.board_subimage)
            self.stone_subimage_boundaries = self.get_stone_subimage_boundaries(
                self.board_subimage, self.intersections
            )

            self.state = self.find_state(
                self.board_subimage,
                self.stone_subimage_boundaries,
                detection_function=detection_function,
                cutoffs=cutoffs,
            )

            if flip:
                self.state = [row[::-1] for row in self.state[::-1]]

            if debug:
                utils.show_intersections(self.board_subimage, self.intersections)
                utils.show_stones(
                    self.board_subimage, self.stone_subimage_boundaries, self.state
                )

    def transform_image(self, image, corners):
        """Create a rectangular board from an opencv image and corner locations.
        Given two corners crop the board to the rectangle defined by those corners.
        Given four corners, run a perspective transform.

        Args:
            image (opencv image): An opencv image a go board.
            corners (list[tuple[int, int]]): A list of (x, y) pairs for the corners of the board.

        Returns:
            board_subimage (opencv image): A rectangular image whose corners are the 1-1 and 19-19 points on the board.

        """
        if len(corners) == 2:
            (xmin, ymin), (xmax, ymax) = corners
            boundary = (xmin, xmax, ymin, ymax)
            board_subimage = utils.crop(image, boundary)

        elif len(corners) == 4:
            board_subimage = utils.perspective_transform(image, corners)
        return board_subimage

    def get_intersections(self, image):
        """Create a 19x19 evenly spaced array of points according to an image.

        Args:
            image (opencv image): A rectangle to be divided into equal parts.

        Returns:
            intersections: A 19x19 array of integer (x, y) coordinates for each intersection.
        """
        _, _, xstep, ystep = self._get_board_params(image)

        x_locs = [round((ind * xstep)) for ind in range(19)]
        y_locs = [round((ind * ystep)) for ind in range(19)]

        intersections = [[(x_loc, y_loc) for x_loc in x_locs] for y_loc in y_locs]

        return intersections

    def get_stone_subimage_boundaries(self, image, intersections):
        """Partition the board into stone regions.

        Boundaries are +- xstep/2 and ystep/2 from the intersection, but care is necessary at corners and edges.

        Args:
            image (opencv image): A rectangle to be divided into equal parts.
            intersections: An evenly spaced 19x19 array of integer (x, y) coordinates for each intersection.

        Returns
            list[list[(xmin, xmax, ymin, ymax)]: A 19x19 array defining the edges of each stone subimage.
        """
        width, height, xstep, ystep = self._get_board_params(image)
        boundaries = [[0 for _ in range(19)] for _ in range(19)]
        for (i, j), loc in self._iterate(intersections):
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

    def find_state(
        self,
        board_subimage,
        stone_subimage_boundaries,
        detection_function=None,
        cutoffs=None,
    ):
        """Create a 19x19 array `state` filled with `empty`, `black` and `white`

        Args:
            board_subimage (opencv image): A rectangular image whose corners are the 1-1 and 19-19 points on the board.
            board_subimage_boundaries: A 19x19 array that define the corners of the stone subimage
            detection_function (function: opencv image -> int): A function to detect stones from an image
            cutoffs (tuple[int, int]): Boundaries to make decisions for the detection function

        Returns:
            state: A 19x19 array of `empty`, `black`, and `white` corresponding to the image and detection function
        """

        state = [["empty" for _ in range(19)] for _ in range(19)]
        for (i, j), boundary in self._iterate(stone_subimage_boundaries):
            stone_subimage = utils.crop(board_subimage, boundary)
            position_state, deciding_value = self.detect_stone(
                stone_subimage,
                detection_function=detection_function,
                cutoffs=cutoffs,
            )
            state[i][j] = position_state

        return state

    def detect_stone(self, stone_subimage, detection_function=None, cutoffs=None):
        """Run detection functions based on a stone subimage.

        Args:
            stone_subimage (opencv image): Maximal image around a stone.
            detection_function (function: opencv image -> int): Type of stone detection to do.
            cutoffs (tuple[int, int]): Values to distinguish between black, empty, and white.

        Returns:
            position_state (str): Either `'black'`, `'empty'`, or `'white'`.
            deciding_value (float): The value used to make the decision.
        """
        if detection_function == None:
            detection_function = utils.check_bgr_blue
        if cutoffs == None:
            cutoffs = (70, 150)

        deciding_value = detection_function(stone_subimage)
        position_state = self._find_region(deciding_value, cutoffs)

        return position_state, deciding_value

    def compare_to(self, other_board):
        """Compare this board state with another board.

        Args:
            other_board (Board): Another board object with which to compare this one.

        returns:
            missing_stones (list(i, j, board_value, other_board_value): Position and values of states that do not match.
        """
        board_state = self.state

        missing_stones = []

        for (i, j), board_value in self._iterate(board_state):
            other_board_value = other_board.state[i][j]
            if board_value != other_board_value:
                missing_stones.append((i, j, board_value, other_board_value))
        return missing_stones

    def calibrate(
        self, black_stones=None, white_stones=None, empty_spaces=None, verbose=False
    ):
        """Runs several detection functions to see if they can distinguish
        between white stones, black stones, and empty spaces.

        Args:
            black_stones (list[tuple[int, int]]): A list of black stone locations.
            white_stones (list[tuple[int, int]]): A list of white stone locations.
            empty_spaces (list[tuple[int, int]]): A list of empty board spaces.

        returns:
            best_function (function: opencv image -> int): The detection function which differentiates the most between the board values.
            cutoffs (tuple[int, int]): Halfway between the different board value readings for best_function.
        """
        if None in [black_stones, white_stones, empty_spaces]:
            raise ValueError(
                "Please provide black stones, white stones, and empty spaces for calibration."
            )

        board_subimage = self.board_subimage
        stone_subimage_boundaries = self.stone_subimage_boundaries

        black_stone_images = [
            utils.crop(board_subimage, stone_subimage_boundaries[i][j])
            for i, j in black_stones
        ]
        white_stone_images = [
            utils.crop(board_subimage, stone_subimage_boundaries[i][j])
            for i, j in white_stones
        ]
        empty_space_images = [
            utils.crop(board_subimage, stone_subimage_boundaries[i][j])
            for i, j in empty_spaces
        ]

        test_functions = [
            utils.check_bgr_blue,
            utils.check_bgr_subimage,

            utils.check_hsv_value,

            utils.check_bw,
            utils.check_bw_subimage,

            utils.check_bgr_and_bw,

            utils.check_max_difference,
            utils.check_subimage_max_difference,

            utils.check_sum,            
        ]

        max_score = 0

        best_function = None
        boundaries = None

        for measurement_function in test_functions:
            b_measurements = [measurement_function(im) for im in black_stone_images]
            e_measurements = [measurement_function(im) for im in empty_space_images]
            w_measurements = [measurement_function(im) for im in white_stone_images]

            max_b = max(b_measurements)
            min_e = min(e_measurements)
            max_e = max(e_measurements)
            min_w = min(w_measurements)

            score = min_e - max_b + min_w - max_e


            if (max_b < min_e) and (max_e < min_w):
                if verbose:
                    print(
                        "{} partitions with gaps of size {} and {}".format(
                            measurement_function.__name__, min_e - max_b, min_w - max_e
                        )
                    )
                if score > max_score:
                    max_score = score
                    best_function = measurement_function
                    boundaries = ((max_b + min_e) // 2, (max_e + min_w) // 2)

            else:
                if verbose:
                    print("{} does not partition".format(measurement_function.__name__))

            if verbose:
                print("{} | {} | {}\n".format(max_b, [min_e, max_e], min_w))

        print("")
        if best_function is not None:
            return best_function, boundaries

        else:
            raise ValueError("No partitions of the space found.")

    @staticmethod
    def _iterate(two_dim_array):
        for i, row in enumerate(two_dim_array):
            for j, value in enumerate(row):
                yield ((i, j), value)

    @staticmethod
    def _get_board_params(image):
        height, width, _ = image.shape
        return width, height, width / 18, height / 18

    @staticmethod
    def _human_readable_numeric(loc):
        row, col = loc
        return "{}-{}".format(col + 1, 19 - row)

    @staticmethod
    def _human_readable_alpha(loc):
        row, col = loc
        alpha = "ABCDEFGHJKLMNOPQRST"
        return "{}{}".format(alpha[col], 19 - row)

    @staticmethod
    def _find_region(deciding_value, cutoffs):
        min_cutoff, max_cutoff = cutoffs
        if deciding_value < min_cutoff:
            position_state = "black"
        elif deciding_value > max_cutoff:
            position_state = "white"
        else:
            position_state = "empty"
        return position_state

    @staticmethod
    def _sort_corners(corners):
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
