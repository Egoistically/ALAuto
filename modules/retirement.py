from util.logger import Logger
from util.utils import Utils, Region


class RetirementModule(object):

    def __init__(self, config, stats):
        """Initializes the Retirement module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.config = config
        self.stats = stats
        self.sorted = False
        self.last_retire = 0

    def retirement_logic_wrapper(self, forced=False):
        """Method that fires off the necessary child methods that encapsulates
        the entire action filtering and retiring ships

        Args:
            forced: Forces retirement to start even if need_to_retire returns False.
        """
        if self.need_to_retire or forced is True:
            self.last_retire = self.stats.combat_done
            Logger.log_msg("Opening build menu to retire ships.")

            while True:
                Utils.update_screen()
                
                if Utils.find("menu/button_sort"):
                    # Tap menu retire button
                    Utils.touch_randomly(Region(549, 735, 215, 64))
                    Utils.script_sleep(1)
                    continue
                # In case function is called from menu
                if Utils.find("menu/button_battle"):
                    Utils.touch_randomly(Region(1452, 1007, 198, 52))
                    Utils.script_sleep(1)
                    continue
                if Utils.find("menu/build"):
                    if Utils.find("event/build_limited"):
                        Utils.touch_randomly(Region(30, 816, 94, 94))
                    else:
                        Utils.touch_randomly(Region(20, 661, 115, 99))
                    Utils.script_sleep(1)
                    continue
                if Utils.find("retirement/selected_none"):
                    self.retire_ships()
                    Utils.touch_randomly(Region(54, 57, 67, 67))
                    return

    def retire_ships(self):
        while True:
            Utils.update_screen()

            if Utils.find("retirement/selected_none") and self.sorted == False:
                Logger.log_debug("Opening sorting menu.")
                Utils.touch_randomly(Region(1655, 14, 130, 51))
                continue
            if Utils.find("retirement/button_sort_all", 0.99):
                Logger.log_debug("Changing sorting options for retirement.")
                Utils.touch_randomly(Region(672, 724, 185, 41))
                Utils.script_sleep(0.5)
                Utils.touch_randomly(Region(911, 724, 185, 41))
                Utils.script_sleep(0.5)
                continue
            if Utils.find("retirement/button_sort_common") and Utils.find("retirement/button_sort_rare"):
                Logger.log_msg("Sorting options for retirement are correct.")
                self.sorted = True
                Utils.touch_randomly(Region(1090, 969, 220, 60))
                Utils.script_sleep(1)
                continue
            if Utils.find("retirement/empty"):
                Logger.log_msg("No ships left to retire.")
                Utils.touch_randomly(Region(54, 57, 67, 67))
                return
            if Utils.find("retirement/selected_none"):
                self.select_ships()
                continue
            if Utils.find("retirement/bonus"):
                self.handle_retirement()
                continue

    def select_ships(self):
        Logger.log_msg("Selecting ships for retirement.") 

        for i in range(0, 7):
            Utils.touch_randomly(Region(209 + (i * 248), 238, 70, 72))

    def handle_retirement(self):
        Utils.touch_randomly(Region(1510, 978, 216, 54))
        items_found = 0

        while True:
            Utils.update_screen()

            if Utils.find("retirement/alert_bonus"):
                Utils.touch_randomly(Region(1412, 938, 218, 61))
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                Utils.script_sleep(1)
                items_found += 1
                if items_found > 1:
                    return
                continue
            if Utils.find("retirement/alert_info"):
                Utils.touch_randomly(Region(1320, 785, 232, 62))
                Utils.script_sleep(1)
                continue
            if Utils.find("retirement/button_disassemble"):
                Utils.touch_randomly(Region(1099, 827, 225, 58))
                Utils.script_sleep(1)
                continue

    @property
    def need_to_retire(self):
        """Checks whether the script needs to retire ships

        Returns:
            bool: True if the script needs to retire ships
        """
        # check if it has already retired with current combat count so it doesn't enter a loop
        if self.stats.combat_done > self.last_retire:
            return self.stats.combat_done % int(self.config.combat['retire_cycle']) == 0
