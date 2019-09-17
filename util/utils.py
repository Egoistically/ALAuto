import cv2
import numpy
import time
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from random import uniform, gauss, randint
from scipy import spatial
from util.adb import Adb
from util.logger import Logger

class Region(object):
    x, y, w, h = 0, 0, 0, 0

    def __init__(cls, x, y, w, h):
        """Initializes a region.

        Args:
            x (int): Initial x coordinate of the region (top-left).
            y (int): Initial y coordinate of the region (top-left).
            w (int): Width of the region.
            h (int): Height of the region.
        """
        cls.x = x
        cls.y = y
        cls.w = w
        cls.h = h

screen = None

class Utils(object):

    DEFAULT_SIMILARITY = 0.95
    locations = ()

    @staticmethod
    def multithreader(threads):
        """Method for starting and threading multithreadable Threads in
        threads.

        Args:
            threads (list): List of Threads to multithread.
        """
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    @staticmethod
    def script_sleep(base=None, flex=None):
        """Method for putting the program to sleep for a random amount of time.
        If base is not provided, defaults to somewhere along with 0.3 and 0.7
        seconds. If base is provided, the sleep length will be between base
        and 2*base. If base and flex are provided, the sleep length will be
        between base and base+flex. The global SLEEP_MODIFIER is than added to
        this for the final sleep length.

        Args:
            base (int, optional): Minimum amount of time to go to sleep for.
            flex (int, optional): The delta for the max amount of time to go
                to sleep for.
        """
        if base is None:
            time.sleep(uniform(0.4, 0.7))
        else:
            flex = base if flex is None else flex
            time.sleep(uniform(base, base + flex))

    @staticmethod
    def update_screen():
        """Uses ADB to pull a screenshot of the device and then read it via CV2
        and then returns the read image.

        Returns:
            image: A CV2 image object containing the current device screen.
        """
        global screen
        screen = None
        while screen is None:
            screen = cv2.imdecode(numpy.fromstring(Adb.exec_out(r"screencap -p | sed s/\r\n/\n/"),dtype=numpy.uint8),0)

    @staticmethod
    def find(image, similarity=DEFAULT_SIMILARITY):
        """Finds the specified image on the screen

        Args:
            image (string): [description]
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.

        Returns:
            Region: region object containing the location and size of the image
        """
        template = cv2.imread('assets/{}.png'.format(image), 0)
        width, height = template.shape[::-1]
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if (value >= similarity):
            return Region(location[0], location[1], width, height)
        return None

    @classmethod
    def find_all(cls, image, similarity=DEFAULT_SIMILARITY):
        """Finds all locations of the image on the screen

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            array: Array of all coordinates where the image appears
        """
        del cls.locations
        template = cv2.imread('assets/{}.png'.format(image), 0)
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        cls.locations = numpy.where(match >= similarity)

        pool = ThreadPool(processes=2)
        count = 0.85

        while len(cls.locations[0] < 2) and (count < 1.10):
            result = pool.apply_async(cls.match_resize, (template, count, similarity))
            cls.script_sleep(0.01)
            count += 0.01

        pool.close()
        return cls.filter_similar_coords(
            list(zip(cls.locations[1], cls.locations[0])))

    @classmethod
    def match_resize(cls, image, scale, similarity=DEFAULT_SIMILARITY):
        template_resize = cv2.resize(image, None, fx = scale, fy = scale, interpolation = cv2.INTER_CUBIC)
        match_resize = cv2.matchTemplate(screen, template_resize, cv2.TM_CCOEFF_NORMED)
        numpy.append(cls.locations, numpy.where(match_resize >= similarity))

    @classmethod
    def touch(cls, coords):
        """Sends an input command to touch the device screen at the specified
        coordinates via ADB

        Args:
            coords (array): An array containing the x and y coordinate of
                where to touch the screen
        """
        Adb.shell("input swipe {} {} {} {} {}".format(coords[0], coords[1], coords[0], coords[1], randint(50, 120)))
        cls.script_sleep()

    @classmethod
    def touch_randomly(cls, region=Region(0, 0, 1280, 720)):
        """Touches a random coordinate in the specified region

        Args:
            region (Region, optional): Defaults to Region(0, 0, 1280, 720).
                specified region in which to randomly touch the screen
        """
        x = cls.random_coord(region.x, region.x + region.w)
        y = cls.random_coord(region.y, region.y + region.h)
        cls.touch([x, y])

    @classmethod
    def swipe(cls, x1, y1, x2, y2, ms):
        """Sends an input command to swipe the device screen between the
        specified coordinates via ADB

        Args:
            x1 (int): x-coordinate to begin the swipe at.
            y1 (int): x-coordinate to end the swipe at.
            x2 (int): y-coordinate to begin the swipe at.
            y2 (int): y-coordinate to begin the swipe at.
            ms (int): Duration in ms of swipe.
        """
        Adb.shell("input swipe {} {} {} {} {}".format(x1, y1, x2, y2, ms))
        cls.update_screen()

    @classmethod
    def find_and_touch(cls, image, similarity=DEFAULT_SIMILARITY):
        """Finds the image on the screen and touches it if it exists

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.

        Returns:
            bool: True if the image was found and touched, false otherwise
        """
        region = cls.find(image, similarity)
        if region is not None:
            cls.touch_randomly(region)
            return True
        return False

    @classmethod
    def wait_and_touch(cls, image, seconds, similarity=DEFAULT_SIMILARITY):
        """Periodically searches the screen during the specified amount of time
        for the specified image on the screen and touches it

        Args:
            image (string): Name of the image.
            seconds (int): Number of seconds to continuously search for the
                image and then touch it if it exists.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            bool: True if the image was found and touched, false otherwise
        """
        limit = datetime.now() + timedelta(seconds=seconds)
        while (datetime.now() < limit):
            if cls.find_and_touch(image, similarity):
                return True
        return False

    @classmethod
    def touch_all(cls, image, similarity=DEFAULT_SIMILARITY):
        """Finds all locations of the image on the screen and touches them

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            bool: True if any images were touched, false otherwise
        """
        template = cv2.imread('assets/{}.png'.format(image), 0)
        width, height = template.shape[::-1]
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        locations = numpy.where(match >= similarity)
        if locations:
            for i in range(0, len(locations[0])):
                x1 = locations[1][i]
                x2 = x1 + width
                y1 = locations[0][i]
                y2 = y1 + height
                cls.touch([cls.random_coord(x1, x2),
                           cls.random_coord(y1, y2)])
                cls.script_sleep(1)
                cls.touch_randomly
                cls.script_sleep(1)
            return True
        return False

    @classmethod
    def wait_and_find(cls, image, seconds, similarity=DEFAULT_SIMILARITY):
        """Periodically searches the screen during the specified amount of time
        for the specified image on the screen and touches it

        Args:
            image (string): Name of the image.
            seconds (int): Number of seconds to continuously search for the
                image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            region: Returns Region object containing the location and size of
            the image if found
        """
        limit = datetime.now() + timedelta(seconds=seconds)
        while (datetime.now() < limit):
            region = cls.find(image, similarity)
            if region is not None:
                return region
        return None

    @classmethod
    def scroll_find(cls, image, x_dist, y_dist,
                    similarity=DEFAULT_SIMILARITY):
        """Looks around the screen in a clockwise direction for the image.

        Args:
            image (string): Name of the image.
            x_dist (int): Distance in which to swipe the screen horizontally.
            y_dist (int): Distance in which to swipe the screen vertically.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match
        """
        swipe_areas = [
            [640, 360 - y_dist, 640, 360 + y_dist, 300],
            [640 + x_dist, 360, 640 - x_dist, 360, 300],
            [640, 360 + y_dist * 1.5, 640, 360 - y_dist * 1.5, 300],
            [640 - x_dist * 1.5, 360, 640 + x_dist * 1.5, 360, 300]]
        for area in swipe_areas:
            region = cls.find(image, similarity)
            if region is not None:
                return region
            cls.swipe(area[0], area[1], area[2], area[3], area[4])
        return None

    @classmethod
    def exists(cls, image, similarity=DEFAULT_SIMILARITY):
        """Checks whether the image exists on the screen.

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            bool: True if the image exists on the screen, false otherwise
        """
        return cls.find(image, similarity) is not None

    @classmethod
    def wait_for_exist(cls, image, duration, similarity=DEFAULT_SIMILARITY):
        """Wait for the specified number of seconds for the image to exist on
        the screen.

        Args:
            image (string): Name of the image.
            duration (int): Duration in seconds to wait for the image to exist.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match

        Returns:
            bool: True if the image exists on the screen, false otherwise
        """
        limit = datetime.now() + timedelta(seconds=duration)
        while (datetime.now() < limit):
            if cls.exists(image, similarity):
                return True
        return False

    @classmethod
    def random_coord(cls, min_val, max_val):
        """Wrapper method that calls cls._randint() or cls._random_coord() to
        generate the random coordinate between min_val and max_val, depending
        on which return line is enabled.

        Args:
            min_val (int): Minimum value of the random number.
            max_val (int): Maximum value of the random number.

        Returns:
            int: The generated random number
        """
        return cls._randint(min_val, max_val)
        # return cls._randint_gauss(min_val, max_val)

    @staticmethod
    def _randint(min_val, max_val):
        """Method to generate a random value based on the min_val and max_val
        with a uniform distribution.

        Args:
            min_val (int): Minimum value of the random number.
            max_val (int): Maximum value of the random number.

        Returns:
            int: The generated random number
        """
        return randint(min_val, max_val)

    @staticmethod
    def _randint_gauss(min_val, max_val):
        """Method to generate a random value based on the min_val and max_val
        with a gaussian (normal) distribution.

        Args:
            min_val (int): minimum value of the random number
            max_val (int): maximum value of the random number

        Returns:
            int: the generated random number
        """
        summed_val = float(min_val) + float(max_val)
        diff = float(abs(min_val) - abs(max_val))

        mu = summed_val / 2
        sigma = diff / 6

        return int(max(min_val, min(gauss(mu, sigma), max_val)))

    @classmethod
    def filter_similar_coords(cls, coords):
        """Filters out coordinates that are close to each other.

        Args:
            coords (array): An array containing the coordinates to be filtered.

        Returns:
            array: An array containing the filtered coordinates.
        """
        #print("c " + str(coords))
        filtered_coords = []
        if len(coords) > 0:
            filtered_coords.append(coords[0])
            for coord in coords:
                if cls.find_closest(filtered_coords, coord)[0] > 40:
                    filtered_coords.append(coord)
        #print("fc " + str(filtered_coords))
        return filtered_coords

    @staticmethod
    def find_closest(coords, coord):
        """Utilizes a k-d tree to find the closest coordiante to the specified
        list of coordinates.

        Args:
            coords (array): Array of coordinates to search.
            coord (array): Array containing x and y of the coordinate.

        Returns:
            array: An array containing the distance of the closest coordinate
            in the list of coordinates to the specified coordinate as well the
            index of where it is in the list of coordinates
        """
        return spatial.KDTree(coords).query(coord)
