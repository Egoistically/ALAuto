import cv2
import numpy
import time
from imutils import contours, grab_contours
from multiprocessing.pool import ThreadPool
from datetime import datetime, timedelta
from random import uniform, gauss, randint
from scipy import spatial
from util.adb import Adb
from util.logger import Logger

class Region(object):
    x, y, w, h = 0, 0, 0, 0

    def __init__(self, x, y, w, h):
        """Initializes a region.

        Args:
            x (int): Initial x coordinate of the region (top-left).
            y (int): Initial y coordinate of the region (top-left).
            w (int): Width of the region.
            h (int): Height of the region.
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h

screen = None
last_ocr = ''

class Utils(object):

    small_boss_icon = False
    DEFAULT_SIMILARITY = 0.95
    assets = ''
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
            if Adb.legacy:
                screen = cv2.imdecode(numpy.fromstring(Adb.exec_out(r"screencap -p | sed s/\r\n/\n/"),dtype=numpy.uint8),0)
            else:
                screen = cv2.imdecode(numpy.fromstring(Adb.exec_out('screencap -p'), dtype=numpy.uint8), 0)

    @classmethod
    def wait_update_screen(cls, time=None):
        """Delayed update screen.

        Args:
            time (int, optional): seconds of delay.
        """
        if time is None:
            cls.script_sleep()
        else:
            cls.script_sleep(time)
        cls.update_screen()

    @staticmethod
    def read_numbers(x, y, w, h, max_digits=5):
        """ Method to ocr numbers.
            Returns int.
        """
        text = []

        crop = screen[y:y+h, x:x+w]
        crop = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        thresh = cv2.threshold(crop, 0, 255, cv2.THRESH_OTSU)[1]

        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnts = grab_contours(cnts)
        cnts = contours.sort_contours(cnts, method="left-to-right")[0]

        if len(cnts) > max_digits:
            return 0

        for c in cnts:
            scores = []

            (x, y, w, h) = cv2.boundingRect(c)
            roi = thresh[y:y + h, x:x + w]
            row, col = roi.shape[:2]

            width = round(abs((50 - col)) / 2) + 5
            height = round(abs((94 - row)) / 2) + 5
            resized = cv2.copyMakeBorder(roi, top=height, bottom=height, left=width, right=width, borderType=cv2.BORDER_CONSTANT, value=[0, 0, 0])

            for x in range(0,10):
                template = cv2.imread("assets/numbers/{}.png".format(x), 0)

                result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
                (_, score, _, _) = cv2.minMaxLoc(result)
                scores.append(score)

            text.append(str(numpy.argmax(scores)))

        text = "".join(text)
        return int(text)

    @classmethod
    def check_oil(cls, limit=0):
        global last_ocr
        oil = []

        if limit == 0:
            return True

        cls.menu_navigate("menu/button_battle")

        while len(oil) < 5:
            _res = int(cls.read_numbers(970, 38, 101, 36))
            if last_ocr == '' or abs(_res - last_ocr) < 600:
                oil.append(_res)

        last_ocr = max(set(oil), key=oil.count)
        Logger.log_debug("Current oil: " + str(last_ocr))

        if limit > last_ocr:
            Logger.log_error("Oil below limit: " + str(last_ocr))
            return False

        return last_ocr

    @classmethod
    def menu_navigate(cls, image):
        cls.update_screen()

        while not cls.find(image, 0.85):
            if image == "menu/button_battle":
                cls.touch_randomly(Region(54, 57, 67, 67))
                cls.wait_update_screen(1)

        return

    @classmethod
    def find(cls, image, similarity=DEFAULT_SIMILARITY):
        """Finds the specified image on the screen

        Args:
            image (string): [description]
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.

        Returns:
            Region: region object containing the location and size of the image
        """
        template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
        width, height = template.shape[::-1]
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if (value >= similarity):
            return Region(location[0], location[1], width, height)
        return None

    @classmethod
    def find_in_scaling_range(cls, image, similarity=DEFAULT_SIMILARITY, lowerEnd=0.8, upperEnd=1.2):
        """Finds the location of the image on the screen. First the image is searched at its default scale,
        and if it isn't found, it will be resized using values inside the range provided until a match that satisfy
        the similarity value is found. If the image isn't found even after it has been resized, the method returns None.

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match
            lowerEnd (float, optional): Defaults to 0.8.
                Lowest scaling factor used for resizing.
            upperEnd (float, optional): Defaults to 1.2.
                Highest scaling factor used for resizing.

        Returns:
            Region: Coordinates or where the image appears.
        """
        template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
        # first try with default size
        width, height = template.shape[::-1]
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if (value >= similarity):
            return Region(location[0], location[1], width, height)

        # resize and match using threads

        # change scaling factor if the boss icon searched is small
        # (some events has as boss fleet a shipgirl with a small boss icon at her bottom right)
        if cls.small_boss_icon and image == 'enemy/fleet_boss':
            lowerEnd = 0.4
            upperEnd = 0.6

        # preparing interpolation methods        
        middle_range = (upperEnd + lowerEnd)/2.0
        if lowerEnd < 1 and upperEnd > 1 and middle_range == 1:
            l_interpolation = cv2.INTER_AREA
            u_interpolation = cv2.INTER_CUBIC
        elif upperEnd < 1 and lowerEnd < upperEnd:
            l_interpolation = cv2.INTER_AREA
            u_interpolation = cv2.INTER_AREA
        elif lowerEnd > 1 and upperEnd > lowerEnd:
            l_interpolation = cv2.INTER_CUBIC
            u_interpolation = cv2.INTER_CUBIC
        else:
            l_interpolation = cv2.INTER_NEAREST
            u_interpolation = cv2.INTER_NEAREST

        results_list = []
        regions_detected = []
        count = 0
        loop_limiter = (middle_range - lowerEnd)*100

        # creating and launching worker processes
        pool = ThreadPool(processes=4)

        while (upperEnd > lowerEnd) and (count < loop_limiter):
            l_result = pool.apply_async(cls.resize_and_match, (template, lowerEnd, similarity, l_interpolation))
            u_result = pool.apply_async(cls.resize_and_match, (template, upperEnd, similarity, u_interpolation))
            cls.script_sleep(0.01)
            lowerEnd+=0.02
            upperEnd-=0.02
            count +=1
            results_list.append(l_result)
            results_list.append(u_result)
        
        # closing pool and waiting for results
        pool.close()
        pool.join()

        # extract regions from async_result
        for i in range(0, len(results_list)):
            if results_list[i].get() is not None:
                regions_detected.append(results_list[i].get())

        if (len(regions_detected)>0):
            return regions_detected[0]
        else:
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
        template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
        match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        cls.locations = numpy.where(match >= similarity)

        pool = ThreadPool(processes=4)
        count = 1.20
        results_list = []

        while (len(cls.locations[0]) < 1) and (count > 0.80):
            result = pool.apply_async(cls.match_resize, (template, count, similarity))
            count -= 0.02
            results_list.append(result)
            result = pool.apply_async(cls.match_resize, (template, count, similarity))
            cls.script_sleep(0.01)
            count -= 0.02
            results_list.append(result)

        pool.close()
        pool.join()

        # extracting locations from pool's results
        for i in range(0, len(results_list)):
            cls.locations = numpy.append(cls.locations, results_list[i].get(), axis=1)

        return cls.filter_similar_coords(
            list(zip(cls.locations[1], cls.locations[0])))

    @classmethod
    def match_resize(cls, image, scale, similarity=DEFAULT_SIMILARITY):
        template_resize = cv2.resize(image, None, fx = scale, fy = scale, interpolation = cv2.INTER_NEAREST)
        match_resize = cv2.matchTemplate(screen, template_resize, cv2.TM_CCOEFF_NORMED)
        return numpy.where(match_resize >= similarity)

    @classmethod
    def resize_and_match(cls, templateImage, scale, similarity=DEFAULT_SIMILARITY, interpolationMethod=cv2.INTER_NEAREST):
        template_resize = cv2.resize(templateImage, None, fx = scale, fy = scale, interpolation = interpolationMethod)
        width, height = template_resize.shape[::-1]
        match = cv2.matchTemplate(screen, template_resize, cv2.TM_CCOEFF_NORMED)
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if (value >= similarity):
             return Region(location[0], location[1], width, height)

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
    def touch_randomly(cls, region=Region(0, 0, 1920, 1080)):
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
            y1 (int): y-coordinate to begin the swipe at.
            x2 (int): x-coordinate to end the swipe at.
            y2 (int): y-coordinate to end the swipe at.
            ms (int): Duration in ms of swipe. This value shouldn't be lower than 300, better if it is higher.
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

    @classmethod
    def filter_similar_coords(cls, coords):
        """Filters out coordinates that are close to each other.

        Args:
            coords (array): An array containing the coordinates to be filtered.

        Returns:
            array: An array containing the filtered coordinates.
        """
        Logger.log_debug("Coords: " + str(coords))
        filtered_coords = []
        if len(coords) > 0:
            filtered_coords.append(coords[0])
            for coord in coords:
                if cls.find_closest(filtered_coords, coord)[0] > 40:
                    filtered_coords.append(coord)
        Logger.log_debug("Filtered Coords: " + str(filtered_coords))
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
