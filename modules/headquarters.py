from util.utils import Region, Utils
from util.logger import Logger
from util.stats import Stats
from util.config import Config
import numpy as np


class HeadquartersModule(object):

    def __init__(self, config, stats):
        """Initializes the HQ module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.region = {
            'hq_tab': Region(745, 1000, 205, 65),
            'tap_out': Region(760, 865, 380, 105),
            'dorm_tab': Region(845, 390, 260, 295),
            'academy_tab': Region(255, 390, 260, 295),
            'dorm_back_button': Region(21, 47, 65, 65),
            'dorm_eye_button': Region(27, 223, 50, 47),
            'supplies_bar': Region(310, 975, 215, 65),
            'oxy_cola': Region(470, 580, 105, 90),
            'exit_snacks_menu': Region(900, 880, 380, 135),
            'button_back': Region(48, 43, 76, 76),
            'confirm_dorm_summary': Region(1545, 905, 235, 65),
            'ignore_give_food_button': Region(690, 750, 185, 60),
            'tactical_class_building': Region(1050, 195, 115, 64),
            'start_lesson_button': Region(1660, 900, 150, 60),
            'cancel_lesson_button': Region(1345, 900, 170, 60)
        }

        if self.config.dorm['enabled']:
            self.supply_region = list()
            self.supply_order = list()
            self.supply_whiteout_threshold = 220
            self.start_feed_threshold = 0.2
            self.stop_feed_threshold = 0.8

            gap = 235
            supplies = [1000, 2000, 3000, 5000, 10000, 20000]

            for i in range(6):
                self.supply_region.append(Region(450 + i * gap, 520, 100, 100))
            for val in config.dorm['AvailableSupplies']:
                self.supply_order.append(supplies.index(val))


    def hq_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        all the actions related to the headquarters tab.
        These actions are:
        - Collecting dorm tokens/affinity points
        - Refilling dorm
        - Skill levelling
        """
        Logger.log_msg("Found HQ  alert.")
        Utils.touch_randomly(self.region["hq_tab"])

        # counter variables are used to prevent longer loops, i.e. when their corresponding alerts get stuck
        counterHQ = 0
        counterAcademy = 0
        counterDorm = 0

        while True:
            Utils.wait_update_screen(1)

            if self.config.academy['enabled'] and counterAcademy < 2 and Utils.find("headquarters/academy_alert", 0.99):
                Logger.log_msg("Found academy alert.")
                # open academy
                Utils.touch_randomly(self.region["academy_tab"])
                Utils.script_sleep(2)
                # open tactical class
                Logger.log_debug("Opening tactical class.")
                Utils.touch_randomly(self.region["tactical_class_building"])
                self.skill_levelling()
                # exit academy
                Utils.touch_randomly(self.region["button_back"])
                counterAcademy += 1
                Logger.log_debug("Going back to main menu.")
                continue
            if self.config.dorm['enabled'] and counterDorm < 3 and Utils.find("headquarters/dorm_alert", 0.99):
                Logger.log_msg("Found dorm alert.")
                # open the dorm
                Utils.touch_randomly(self.region["dorm_tab"])
                Logger.log_debug("Opening tactical class.")
                self.refill_dorm()
                self.collect_dorm_balloons()
                Utils.script_sleep(1)
                Logger.log_msg("Cleaned dorm.")
                # exit dorm
                Utils.touch_randomly(self.region["dorm_back_button"])
                counterDorm += 1
                Logger.log_debug("Going back to main menu.")
                continue
            if Utils.find("headquarters/cat_lodge_alert", 0.99):
                # if only the cat lodge alert is detected as valid alert, ignore it
                Logger.log_msg("Cat lodge alert detected, ignoring it.")
            if counterHQ < 5 and Utils.find("headquarters/hq_alert"):
                # counterHQ = 5 only if academy has been opened two times and dorm three times
                # the find fails if it's on the main menu and there is no alert or if it is on the selection screen
                Logger.log_msg("Found HQ  alert.")
                Utils.touch_randomly(self.region["hq_tab"])
                counterHQ += 1
                continue
            else:
                # exit loop
                if Utils.find("headquarters/dorm_sign"):
                    # academy alert is stuck or dorm alert is stuck or cat lodge alert is on
                    Logger.log_debug("Alert is on, but nothing else to do.")
                    Utils.touch_randomly(self.region["tap_out"])
                Logger.log_debug("Ending HQ loop.")
                break

        Utils.wait_update_screen(1)
        return True

    def collect_dorm_balloons(self):
        """"
        This method finds and collects all the dorm tokens and affinity points visible to the script.
        The various swipes may not work if there is a shipgirl at the starting point of the swipe.
        For this reason the wrapper to this methoed iterates its cycle for three times, refreshing the dorm.
        """
        Utils.script_sleep(1)
        # tap dorm eye in order to hide UI
        Utils.touch_randomly(self.region["dorm_eye_button"])
        Logger.log_debug("Collecting all visible dorm tokens/affinity points.")

        for i in range(0, 4):
            Utils.wait_update_screen(1)
            # since a rather low similarity is used, the variable j ensures a finite loop
            j = 0
            while Utils.find_and_touch("headquarters/dorm_token", 0.75) and j < 5:
                Logger.log_msg("Collected dorm token.")
                Utils.wait_update_screen()
                j += 1
            j = 0
            while Utils.find_and_touch("headquarters/affinity_point", 0.75) and j < 5:
                Logger.log_msg("Collected affinity points.")
                Utils.wait_update_screen()
                j += 1
            if i == 0:
                # swipe right and refresh
                Utils.swipe(960, 540, 560, 540, 300)
                continue
            if i == 1:
                # swipe left (also countering the previous swipe) and refresh
                Utils.swipe(960, 540, 1760, 540, 300)
                continue
            if i == 2:
                # undo previous swipe
                Utils.swipe(960, 540, 560, 540, 300)
                # swipe up and refresh
                Utils.swipe(960, 540, 960, 790, 300)
                continue
            if i == 3:
                # swipe bottom (also countering the previous swipe) and refresh
                Utils.swipe(960, 540, 960, 40, 300)
                continue

        # restore UI
        Utils.touch_randomly(self.region["dorm_eye_button"])

    def refill_dorm(self):
        """
        This method refill the dorm supplies with 10 oxy cola (150 minutes) if the supplies bar is empty.
        """

        Utils.script_sleep(5)
        Logger.log_debug("Refilling dorm supplies if empty.")

        while True:
            Utils.wait_update_screen(1)
            if Utils.find("headquarters/dorm_summary_confirm_button"):
                # dismiss dorm summary, if any
                Utils.touch_randomly(self.region["confirm_dorm_summary"])
                continue
            if Utils.find("headquarters/give_food_button"):
                # dismiss notification by tapping ignore
                Utils.touch_randomly(self.region["ignore_give_food_button"])
                continue
            if self.get_dorm_bar_empty(self.start_feed_threshold, True):
                # proceed to refill
                self.feed_snacks()
                break
            else:
                # exit loop
                Logger.log_debug("Ending refill loop.")
                break

    def feed_snacks(self):
        Utils.touch_randomly(self.region["supplies_bar"])
        Utils.script_sleep(1)
        Utils.update_screen()
        alert_found = Utils.find("menu/alert_close")
        retry_counter = 0
        while retry_counter < 40 and self.get_dorm_bar_empty(self.stop_feed_threshold) and not alert_found:
            retry_counter += 1
            find_food = False
            for idx in self.supply_order:
                region = self.supply_region[idx]
                if Utils.get_region_color_average(region)[2] < self.supply_whiteout_threshold:
                    Utils.touch_randomly(region)
                    find_food = True
                    break
            if not find_food:
                break
            else:
                Utils.wait_update_screen(0.5)
                alert_found = Utils.find("menu/alert_close")

        if alert_found:
            Utils.touch_randomly(alert_found)
            Utils.wait_update_screen(1)
        # tap out
        Utils.touch_randomly(self.region["exit_snacks_menu"])

    def get_dorm_bar_color(self, percentage, corner_bar):
        if corner_bar:
            x_coord = 45 + int(780 * percentage)
            y_coord = 1025
        else:
            x_coord = 630 + int(880 * percentage)
            y_coord = 400
        return Utils.get_region_color_average(Region(x_coord, y_coord, 10, 10))

    def get_dorm_bar_filled(self, percentage, corner_bar=False):
        return not self.get_dorm_bar_empty(percentage, corner_bar)

    def get_dorm_bar_empty(self, percentage, corner_bar=False):
        low = np.array([0, 0, 0])
        high = np.array([255, 20, 128])
        col = self.get_dorm_bar_color(percentage, corner_bar)
        if np.all((low <= col) & (col <= high)):
            return True
        else:
            return False

    def skill_levelling(self):
        """
        This method ensures that the skills currently being levelled continue to do so.
        The skillbooks used are the ones indicated by the SkillBookTier setting in the config.ini file.
        """
        Utils.script_sleep(5)
        Logger.log_msg("Levelling the skills of the previously chosen ships.")

        while True:
            Utils.wait_update_screen(1)

            if Utils.find_and_touch("menu/button_confirm"):
                Logger.log_msg("Starting/ending skill levelling session.")
                Utils.script_sleep(3.5)
                continue
            if Utils.find("headquarters/skill_exp_gain"):
                if Utils.find_and_touch(
                        "headquarters/t{}_offense_skillbook".format(self.config.academy["skill_book_tier"]), 0.99):
                    # levelling offesinve skill
                    Logger.log_msg("Selected T{} offensive skill book.".format(self.config.academy["skill_book_tier"]))
                    self.stats.increment_offensive_skillbook_used()
                elif Utils.find_and_touch(
                        "headquarters/t{}_defense_skillbook".format(self.config.academy["skill_book_tier"]), 0.99):
                    # levelling defesinve skill
                    Logger.log_msg("Selected T{} defensive skill book.".format(self.config.academy["skill_book_tier"]))
                    self.stats.increment_defensive_skillbook_used()
                elif Utils.find_and_touch(
                        "headquarters/t{}_support_skillbook".format(self.config.academy["skill_book_tier"]), 0.99):
                    # levelling support skill
                    Logger.log_msg("Selected T{} support skill book.".format(self.config.academy["skill_book_tier"]))
                    self.stats.increment_support_skillbook_used()
                else:
                    Logger.log_warning("Skillbook specified not found. Cancelling lesson.")
                    Utils.touch_randomly(self.region["cancel_lesson_button"])
                    continue
                Utils.script_sleep(1)
                Utils.touch_randomly(self.region["start_lesson_button"])
                continue
            if Utils.find("headquarters/tactical_class"):
                # exit tactical class
                Utils.touch_randomly(self.region["button_back"])
                Logger.log_msg("All classes have started.")
                Utils.script_sleep(1)
                break
