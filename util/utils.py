import cv2
import numpy
import time
import struct
import os
import lz4.block
from imutils import contours, grab_contours
from datetime import datetime, timedelta
from random import uniform, gauss, randint
from scipy import spatial
from util.adb import Adb
from util.logger import Logger
from util.config_consts import UtilConsts
from threading import Thread


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

    def equal_approximated(self, region, tolerance=15):
        """Compares this region to the one received and establishes if they are the same
        region tolerating a difference in pixels up to the one prescribed by tolerance.

        Args:
            region (Region): The region to compare to.
            tolerance (int, optional): Defaults to 15.
                Highest difference of pixels tolerated to consider the two Regions equal.
                If set to 0, the method becomes a "strict" equal.
        """
        valid_x = (self.x - tolerance, self.x + tolerance)
        valid_y = (self.y - tolerance, self.y + tolerance)
        valid_w = (self.w - tolerance, self.w + tolerance)
        valid_h = (self.h - tolerance, self.h + tolerance)
        return (valid_x[0] <= region.x <= valid_x[1] and valid_y[0] <= region.y <= valid_y[1] and
                valid_w[0] <= region.w <= valid_w[1] and valid_h[0] <= region.h <= valid_h[1])


    def intersection(self, other):
        """Checks if there is an intersection between the two regions,
        and if that is the case, returns it.
        Taken from https://stackoverflow.com/a/25068722

        Args:
            other (Region): The region to intersect with.

        Returns:
            intersection (Region) or None.
        """
        a = (self.x, self.y, self.x+self.w, self.y+self.h)
        b = (other.x, other.y, other.x+other.w, other.y+other.h)
        x1 = max(min(a[0], a[2]), min(b[0], b[2]))
        y1 = max(min(a[1], a[3]), min(b[1], b[3]))
        x2 = min(max(a[0], a[2]), max(b[0], b[2]))
        y2 = min(max(a[1], a[3]), max(b[1], b[3]))
        if x1<x2 and y1<y2:
            return type(self)(x1, y1, x2-x1, y2-y1)

    def get_center(self):
        """Calculate and returns the center of this region."""
        return [(self.x * 2 + self.w)//2, (self.y * 2 + self.h)//2]

    def contains(self, coords):
        """Checks if the specified coordinates are inside the region.
        Args:
            coords (list or tuple of two elements): x and y coordinates.

        Returns:
            (bool): whether the point is inside the region.
        """
        return (self.x <= coords[0] <= (self.x + self.w)) and (self.y <= coords[1] <= (self.y + self.h))

screen = None
last_ocr = ''
bytepointer = 0


class Utils(object):
    screen = None
    color_screen = None
    small_boss_icon = False
    screencap_mode = None

    DEFAULT_SIMILARITY = 0.95
    assets = ''
    locations = ()

    @classmethod
    def init_screencap_mode(cls,mode):
        consts = UtilConsts.ScreenCapMode

        cls.screencap_mode = mode

        if cls.screencap_mode == consts.ASCREENCAP:
            # Prepare for ascreencap, push the required libraries
            Adb.exec_out('rm /data/local/tmp/ascreencap')
            cpuArc = Adb.exec_out('getprop ro.product.cpu.abi').decode('utf-8').strip()
            sdkVer = int(Adb.exec_out('getprop ro.build.version.sdk').decode('utf-8').strip())
            ascreencaplib = 'ascreencap_{}'.format(cpuArc)
            if sdkVer in range(21, 26) and os.path.isfile(ascreencaplib):
                Adb.cmd('push {} /data/local/tmp/ascreencap'.format(ascreencaplib))
            else:
                Logger.log_warning(
                    'No suitable version of aScreenCap lib is available locally, using ascreencap_local...')
                if os.path.isfile('ascreencap_local'):
                    Adb.cmd('push ascreencap_local /data/local/tmp/ascreencap')
                else:
                    Logger.log_error(
                        'File "ascreencap_local" not found. Please download the appropriate version of aScreenCap for your device from github.com/ClnViewer/Android-fast-screen-capture and save it as "ascreencap_local"')
                    Logger.log_warning('Since aScreenCap is not ready, falling back to normal adb screencap')
                    Utils.useAScreenCap = False
            Adb.shell('chmod 0777 /data/local/tmp/ascreencap')

    @staticmethod
    def reposition_byte_pointer(byteArray):
        """Method to return the sanitized version of ascreencap stdout for devices
            that suffers from linker warnings. The correct pointer location will be saved
            for subsequent screen refreshes
        """
        global bytepointer
        while(byteArray[bytepointer:bytepointer + 4] != b'BMZ1'):
            bytepointer += 1
            if bytepointer >= len(byteArray):
                raise Exception('Repositioning byte pointer failed, corrupted aScreenCap data received')
        return byteArray[bytepointer:]

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

    @classmethod
    def update_screen(cls):
        """Uses ADB to pull a screenshot of the device and then read it via CV2
        and then stores the images in grayscale and color to screen and color_screen, respectively.

        Returns:
            image: A CV2 image object containing the current device screen.
        """
        consts = UtilConsts.ScreenCapMode

        global screen
        screen = None
        color_screen = None
        while color_screen is None:
            if Adb.legacy:
                color_screen = cv2.imdecode(
                    numpy.fromstring(Adb.exec_out(r"screencap -p | sed s/\r\n/\n/"), dtype=numpy.uint8),
                    cv2.IMREAD_COLOR)
            else:
                if cls.screencap_mode == consts.SCREENCAP_PNG:
                    start_time = time.perf_counter()
                    color_screen = cv2.imdecode(numpy.frombuffer(Adb.exec_out('screencap -p'), dtype=numpy.uint8),
                                                cv2.IMREAD_COLOR)
                    elapsed_time = time.perf_counter() - start_time
                    Logger.log_debug("SCREENCAP_PNG took {} ms to complete.".format('%.2f' % (elapsed_time * 1000)))
                elif cls.screencap_mode == consts.SCREENCAP_RAW:
                    start_time = time.perf_counter()
                    pixel_size = 4

                    byte_arr = Adb.exec_out('screencap')
                    header_format = 'III'
                    header_size = struct.calcsize(header_format)
                    if len(byte_arr) < header_size:
                        continue
                    header = struct.unpack(header_format, byte_arr[:header_size])
                    width = header[0]
                    height = header[1]
                    if len(byte_arr) != header_size + width * height * pixel_size:
                        continue
                    tmp = numpy.frombuffer(byte_arr, dtype=numpy.uint8, count=width * height * 4, offset=header_size)
                    rgb_img = tmp.reshape((height, width, -1))
                    color_screen = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
                    elapsed_time = time.perf_counter() - start_time
                    Logger.log_debug("SCREENCAP_RAW took {} ms to complete.".format('%.2f' % (elapsed_time * 1000)))
                elif cls.screencap_mode == consts.ASCREENCAP:
                    start_time = time.perf_counter()
                    raw_compressed_data = Utils.reposition_byte_pointer(
                        Adb.exec_out('/data/local/tmp/ascreencap --pack 2 --stdout'))
                    compressed_data_header = numpy.frombuffer(raw_compressed_data[0:20], dtype=numpy.uint32)
                    if compressed_data_header[0] != 828001602:
                        compressed_data_header = compressed_data_header.byteswap()
                        if compressed_data_header[0] != 828001602:
                            Logger.log_error('If error persists, disable aScreenCap and report traceback')
                            raise Exception(
                                'aScreenCap header verification failure, corrupted image received. HEADER IN HEX = {}'.format(
                                    compressed_data_header.tobytes().hex()))
                    uncompressed_data_size = compressed_data_header[1].item()
                    color_screen = cv2.imdecode(numpy.frombuffer(
                        lz4.block.decompress(raw_compressed_data[20:], uncompressed_size=uncompressed_data_size),
                        dtype=numpy.uint8), cv2.IMREAD_COLOR)
                    elapsed_time = time.perf_counter() - start_time
                    Logger.log_debug("aScreenCap took {} ms to complete.".format('%.2f' % (elapsed_time * 1000)))
                else:
                    raise Exception('Unknown screencap mode')

            screen = cv2.cvtColor(color_screen, cv2.COLOR_BGR2GRAY)
            cls.color_screen = color_screen
            cls.screen = screen

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
    def get_color_screen():
        """Uses ADB to pull a screenshot of the device and then read it via CV2
        and then returns the read image. The image is in a BGR format.

        Returns:
            image: A CV2 image object containing the current device screen.
        """
        color_screen = None
        while color_screen is None:
            if Adb.legacy:
                color_screen = cv2.imdecode(
                    numpy.fromstring(Adb.exec_out(r"screencap -p | sed s/\r\n/\n/"), dtype=numpy.uint8), 1)
            else:
                color_screen = cv2.imdecode(numpy.fromstring(Adb.exec_out('screencap -p'), dtype=numpy.uint8), 1)
        return color_screen

    @classmethod
    def get_mask_from_alpha(cls, image):
        """Calculate the mask of the specified image from its alpha channel.
        The mask returned is a binary image, where the transparent pixels have been blacked.

        Args:
            image (string): image to load and use to calculate the mask.

        Returns:
            mask (numpy array): binary image obtained from the source image's alpha channel.
        """
        source = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), cv2.IMREAD_UNCHANGED)
        # split into BGRA and get A
        alpha_channel = cv2.split(source)[3]
        ret, thresh = cv2.threshold(alpha_channel, 0, 255, cv2.THRESH_BINARY)
        return thresh

    @classmethod
    def get_enabled_ship_filters(cls, filter_categories="rarity"):
        """Method which returns the regions of all the options enabled for the current sorting filter.

        Args:
            filter_categories (string): a string of ';' separated values, which states the filters' categories
                to take into account for the detection.
        Returns:
            regions (list): a list containing the Region objects detected.
        """
        image = cls.get_color_screen()
        categories = filter_categories.split(';')

        # mask area of no interest, effectively creating a roi
        roi = numpy.full((image.shape[0], image.shape[1]), 0, dtype=numpy.uint8)
        if "rarity" in categories:
            cv2.rectangle(roi, (410, 647), (1835, 737), color=(255, 255, 255), thickness=-1)
        if "extra" in categories:
            cv2.rectangle(roi, (410, 758), (1835, 847), color=(255, 255, 255), thickness=-1)

        # preparing the ends of the interval of blue colors allowed, BGR format
        lower_blue = numpy.array([132, 97, 66], dtype=numpy.uint8)
        upper_blue = numpy.array([207, 142, 92], dtype=numpy.uint8)

        # find the colors within the specified boundaries
        mask = cv2.inRange(image, lower_blue, upper_blue)

        # apply roi, result is a black and white image where the white rectangles are the options enabled
        result = cv2.bitwise_and(roi, mask)

        # obtain countours, needed to calculate the rectangles' positions
        cnts = cv2.findContours(result, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = grab_contours(cnts)
        # filter regions with a contour area inferior to 190x45=8550 (i.e. not a sorting option)
        cnts = list(filter(lambda x: cv2.contourArea(x) > 8550, cnts))
        # loop over the contours and extract regions
        regions = []
        for c in cnts:
            # calculates contours perimeter
            perimeter = cv2.arcLength(c, True)
            # approximates perimeter to a polygon with the specified precision
            approx = cv2.approxPolyDP(c, 0.04 * perimeter, True)

            if len(approx) == 4:
                # if approx is a rectangle, get bounding box
                x, y, w, h = cv2.boundingRect(approx)
                # print values
                Logger.log_debug("Region x:{}, y:{}, w:{}, h:{}".format(x, y, w, h))
                # appends to regions' list
                regions.append(Region(x, y, w, h))

        return regions

    @classmethod
    def show_on_screen(cls, coordinates):
        """ Shows the position of the received coordinates on a screenshot
            through green dots. It pauses the script. Useful for debugging.
        """
        color_screen = cls.get_color_screen()
        for coords in coordinates:
            cv2.circle(color_screen, tuple(coords), 5, (0, 255, 0), -1)
        cv2.imshow("targets", color_screen)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return

    @staticmethod
    def draw_region(screen, region, color, thickness):
        """Method which draws a region (a rectangle) on the image (screen) passed as argument.

        Args:
            screen (numpy array): image to draw on.
            region (Region): rectangle which needs to be drawn.
            color (tuple): specifiy the color of the rectangle's lines.
            thickness (int): specify the thickness of the rectangle's lines (-1 for it to be filled).

        See cv2.rectangle() docs.
        """
        cv2.rectangle(screen, (region.x, region.y), (region.x+region.w, region.y+region.h), color=color, thickness=thickness)

    @staticmethod
    def read_numbers(x, y, w, h, max_digits=5):
        """ Method to ocr numbers.
            Returns int.
        """
        text = []

        crop = screen[y:y + h, x:x + w]
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
            resized = cv2.copyMakeBorder(roi, top=height, bottom=height, left=width, right=width,
                                         borderType=cv2.BORDER_CONSTANT, value=[0, 0, 0])

            for x in range(0, 10):
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

        #cls.menu_navigate("menu/button_battle")

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
    def find(cls, image, similarity=DEFAULT_SIMILARITY, color=False):
        """Finds the specified image on the screen

        Args:
            image (string): [description]
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.
            color (boolean): find the image in color screen

        Returns:
            Region: region object containing the location and size of the image
        """
        if color:
            template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), cv2.IMREAD_COLOR)
            match = cv2.matchTemplate(cls.color_screen, template, cv2.TM_CCOEFF_NORMED)
        else:
            template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
            match = cv2.matchTemplate(cls.screen, template, cv2.TM_CCOEFF_NORMED)

        height, width = template.shape[:2]
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if value >= similarity:
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
        middle_range = (upperEnd + lowerEnd) / 2.0
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
        count = 0
        loop_limiter = (middle_range - lowerEnd) * 100

        thread_list = []
        while (upperEnd > lowerEnd) and (count < loop_limiter):
            thread_list.append(Thread(target=cls.resize_and_match, args=(results_list, template, lowerEnd, similarity, l_interpolation)))
            thread_list.append(Thread(target=cls.resize_and_match, args=(results_list, template, upperEnd, similarity, u_interpolation)))
            lowerEnd+=0.02
            upperEnd-=0.02
            count +=1
        cls.multithreader(thread_list)
        if results_list:
            return results_list[0]
        else:
            return None

    @classmethod
    def find_all(cls, image, similarity=DEFAULT_SIMILARITY, useMask=False):
        """Finds all locations of the image on the screen

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.
            useMask (boolean, optional): Defaults to False.
                If set to True, this function uses a different comparison method and
                a mask when searching for match.

        Returns:
            array: Array of all coordinates where the image appears
        """
        del cls.locations

        if useMask:
            comparison_method = cv2.TM_CCORR_NORMED
            mask = cls.get_mask_from_alpha(image)
        else:
            comparison_method = cv2.TM_CCOEFF_NORMED
            mask = None

        template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
        match = cv2.matchTemplate(screen, template, comparison_method, mask=mask)
        cls.locations = numpy.where(match >= similarity)

        return cls.filter_similar_coords(
            list(zip(cls.locations[1], cls.locations[0])))

    @classmethod
    def find_all_with_resize(cls, image, similarity=DEFAULT_SIMILARITY, useMask=False):
        """Finds all locations of the image at default size on the screen.
        If nothing is found, the method proceeds to resize the image within the
        scaling range of (0.8, 1.2) with a step interval of 0.2 and repeats
        the template matching operation for each resized images.

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.
            useMask (boolean, optional): Defaults to False.
                If set to True, this function uses a different comparison method and
                a mask when searching for match.

        Returns:
            array: Array of all coordinates where the image appears
        """
        del cls.locations

        if useMask:
            comparison_method = cv2.TM_CCORR_NORMED
            mask = cls.get_mask_from_alpha(image)
        else:
            comparison_method = cv2.TM_CCOEFF_NORMED
            mask = None

        template = cv2.imread('assets/{}/{}.png'.format(cls.assets, image), 0)
        match = cv2.matchTemplate(screen, template, comparison_method, mask=mask)
        cls.locations = numpy.where(match >= similarity)

        if len(cls.locations[0]) < 1:
            count = 1.20
            thread_list = []
            results_list = []
            while count > 0.80:
                thread_list.append(Thread(target=cls.match_resize, args=(results_list,template,count,comparison_method,similarity,useMask,mask)))
                count -= 0.02
            Utils.multithreader(thread_list)
            for i in range(0, len(results_list)):
                cls.locations = numpy.append(cls.locations, results_list[i], axis=1)

        return cls.filter_similar_coords(
            list(zip(cls.locations[1], cls.locations[0])))

    @classmethod
    def find_siren_elites(cls):
        color_screen = cls.get_color_screen()

        image = cv2.cvtColor(color_screen, cv2.COLOR_BGR2HSV)

        # We use this primarily to pick out elites from event maps. Depending on the event, this may need to be updated with additional masks.
        lower_red = numpy.array([170,100,180])
        upper_red = numpy.array([180,255,255])
        mask = cv2.inRange(image, lower_red, upper_red)

        ret, thresh = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)

        # Build a structuring element to combine nearby contours together.
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)

        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = grab_contours(cnts)
        contours = list(filter(lambda x: cv2.contourArea(x) > 3000, contours))

        locations = []
        for contour in contours:
            hull = cv2.convexHull(contour)
            M = cv2.moments(hull)
            x = round(M['m10'] / M['m00'])
            y = round(M['m01'] / M['m00'])
            approx = cv2.approxPolyDP(hull, 0.04 * cv2.arcLength(contour, True), True)
            bound_x, bound_y, width, height = cv2.boundingRect(approx)
            aspect_ratio = width / float(height)

            # filter out non-Siren matches (non-squares)
            if len(approx) == 4 and 170 <= width <= 230 and 80 <= height <= 180:
                locations.append([x, y])

        return cls.filter_similar_coords(locations)

    @classmethod
    def match_resize(cls, results_list, image, scale, comparison_method, similarity=DEFAULT_SIMILARITY, useMask=False, mask=None):
        template_resize = cv2.resize(image, None, fx = scale, fy = scale, interpolation = cv2.INTER_NEAREST)
        if useMask:
            mask_resize = cv2.resize(mask, None, fx = scale, fy = scale, interpolation = cv2.INTER_NEAREST)
        else:
            mask_resize = None
        match_resize = cv2.matchTemplate(screen, template_resize, comparison_method, mask=mask_resize)
        results_list.append(numpy.where(match_resize >= similarity))

    @classmethod
    def resize_and_match(cls, results_list, templateImage, scale, similarity=DEFAULT_SIMILARITY, interpolationMethod=cv2.INTER_NEAREST):
        template_resize = cv2.resize(templateImage, None, fx = scale, fy = scale, interpolation = interpolationMethod)
        width, height = template_resize.shape[::-1]
        match = cv2.matchTemplate(screen, template_resize, cv2.TM_CCOEFF_NORMED)
        value, location = cv2.minMaxLoc(match)[1], cv2.minMaxLoc(match)[3]
        if (value >= similarity):
            results_list.append(Region(location[0], location[1], width, height))

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
    def find_and_touch(cls, image, similarity=DEFAULT_SIMILARITY, color=False):
        """Finds the image on the screen and touches it if it exists

        Args:
            image (string): Name of the image.
            similarity (float, optional): Defaults to DEFAULT_SIMILARITY.
                Percentage in similarity that the image should at least match.
            color (boolean): find the image in color screen

        Returns:
            bool: True if the image was found and touched, false otherwise
        """
        region = cls.find(image, similarity, color)
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
    def filter_similar_coords(cls, coords, distance=50):
        """Filters out coordinates that are close to each other.

        Args:
            coords (array): An array containing the coordinates to be filtered.
            distance (int): minimum distance at which two set of coordinates
                are no longer considered close.

        Returns:
            array: An array containing the filtered coordinates.
        """
        #Logger.log_debug("Coords: " + str(coords))
        filtered_coords = []
        if len(coords) > 0:
            filtered_coords.append(coords[0])
            for coord in coords:
                if cls.find_closest(filtered_coords, coord)[0] > distance:
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
        return spatial.cKDTree(coords).query(coord)

    @classmethod
    def get_region_color_average(cls, region, hsv=True):
        """
        Get the average color in the region
        :param region: the region to average the color
        :param hsv: return color in HSV if true. BGR otherwise.
        :return:  BGR or HSV color
        """
        crop = cls.color_screen[region.y:region.y + region.h, region.x:region.x + region.w]
        bgr_avg_color = numpy.average(crop, axis=(0, 1)).astype(numpy.uint8)
        bgr_avg_color = numpy.expand_dims(bgr_avg_color, axis=(0, 1))
        if hsv:
            hsv_avg_color = cv2.cvtColor(bgr_avg_color, cv2.COLOR_BGR2HSV)[0, 0, :]
            return hsv_avg_color
        else:
            return bgr_avg_color
