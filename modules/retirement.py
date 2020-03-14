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
        self.region = {
            'combat_sort_button': Region(549, 735, 215, 64),
            'build_menu': Region(1452, 1007, 198, 52),
            'retire_tab_1': Region(20, 661, 115, 99),
            # retire_tab_2 is used when there is wishing well
            'retire_tab_2': Region(30, 816, 94, 94),
            'menu_nav_back': Region(54, 57, 67, 67),
            'sort_filters_button': Region(1655, 14, 130, 51),
            'all_ship_filter': Region(435, 668, 190, 45),
            'common_ship_filter': Region(671, 668, 190, 45),
            'rare_ship_filter': Region(907, 668, 190, 45),
            'confirm_filter_button': Region(1090, 933, 220, 60),
            #Region(209 + (i * 248), 238, 70, 72)
            'select_ship_0': Region(209, 238, 70, 72),
            'select_ship_1': Region(457, 238, 70, 72),
            'select_ship_2': Region(705, 238, 70, 72),
            'select_ship_3': Region(953, 238, 70, 72),
            'select_ship_4': Region(1201, 238, 70, 72),
            'select_ship_5': Region(1449, 238, 70, 72),
            'select_ship_6': Region(1697, 238, 70, 72),
            'confirm_retire_button': Region(1510, 978, 216, 54),
            'confirm_selected_ships_button': Region(1412, 938, 218, 61),
            'tap_to_continue': Region(661, 840, 598, 203),
            'confirm_selected_equipment_button': Region(1320, 785, 232, 62),
            'disassemble_button': Region(1099, 827, 225, 58)
        }

    def retirement_logic_wrapper(self, forced=False):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of filtering and retiring ships

        Args:
            forced: Forces retirement to start even if need_to_retire returns False.
        """
        if self.need_to_retire or forced:
            self.last_retire = self.stats.combat_done
            Logger.log_msg("Opening build menu to retire ships.")

            while True:
                Utils.update_screen()

                if Utils.find("menu/button_sort"):
                    # Tap menu retire button
                    Utils.touch_randomly(self.region['combat_sort_button'])
                    Utils.script_sleep(1)
                    continue
                # In case function is called from menu
                if Utils.find("menu/button_battle"):
                    Utils.touch_randomly(self.region['build_menu'])
                    Utils.script_sleep(1)
                    continue
                if Utils.find("menu/build"):
                    if Utils.find("event/build_limited"):
                        Utils.touch_randomly(self.region['retire_tab_2'])
                    else:
                        Utils.touch_randomly(self.region['retire_tab_1'])
                    Utils.script_sleep(1)
                    continue
                if Utils.find("retirement/selected_none"):
                    self.set_sort()
                    self.retire_ships()
                    Utils.touch_randomly(self.region['menu_nav_back'])
                    return

            Utils.update_screen()

    def set_sort(self):
        Logger.log_debug("Retirement: " + repr(self.config.retirement))
        while not self.sorted:
            Logger.log_debug("Retirement: Opening sorting menu.")
            Utils.touch_randomly(self.region['sort_filters_button'])
            Utils.script_sleep(0.5)
            # Touch the All button to clear any current filter
            Utils.touch_randomly(self.region['all_ship_filter'])
            Utils.script_sleep(0.5)
            if self.config.retirement['commons']:
                Utils.touch_randomly(self.region['common_ship_filter'])
                Utils.script_sleep(0.5)
            if self.config.retirement['rares']:
                Utils.touch_randomly(self.region['rare_ship_filter'])
                Utils.script_sleep(0.5)
            
            # check if correct options are enabled
            # get the regions of enabled options
            options = Utils.get_enabled_ship_filters()
            if len(options) == 0:
                # if the list is empty it probably means that there was an ui update
                # pausing and requesting for user confirmation
                Logger.log_error("No options detected. User's input required.")
                input("Manually fix sorting options. Press Enter to continue...")
                self.sorted = True
            else:
                retirements = (self.config.retirement['commons'], self.config.retirement['rares'])
                checks = [False, False]
                for option in options:
                    # tolerance is set to 25 since the regions chosen for tapping are smaller than the actual ones
                    if self.config.retirement['commons'] and self.region['common_ship_filter'].equal_approximated(option, 25):
                        Logger.log_debug("Retirement: Sorting commons")
                        checks[0] = True
                    if self.config.retirement['rares'] and self.region['rare_ship_filter'].equal_approximated(option, 25):
                        Logger.log_debug("Retirement: Sorting rares")
                        checks[1] = True
                if retirements == tuple(checks) and len(options) <= 2:
                    Logger.log_debug("Retirement: Sorting options confirmed")
                    self.sorted = True
            Utils.touch_randomly(self.region['confirm_filter_button'])
            Utils.script_sleep(1)
            
    def retire_ships(self):
        while True:
            Utils.update_screen()

            if Utils.find("retirement/empty"):
                Logger.log_msg("No ships left to retire.")
                Utils.touch_randomly(self.region['menu_nav_back'])
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
            Utils.touch_randomly(self.region['select_ship_{}'.format(i)])

    def handle_retirement(self):
        Utils.touch_randomly(self.region['confirm_retire_button'])
        items_found = 0

        while True:
            Utils.update_screen()

            if Utils.find("retirement/alert_bonus"):
                Utils.touch_randomly(self.region['confirm_selected_ships_button'])
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(self.region['tap_to_continue'])
                Utils.script_sleep(1)
                items_found += 1
                if items_found > 1:
                    return
                continue
            if Utils.find("menu/alert_info"):
                Utils.touch_randomly(self.region['confirm_selected_equipment_button'])
                Utils.script_sleep(1)
                continue
            if Utils.find("retirement/button_disassemble"):
                Utils.touch_randomly(self.region['disassemble_button'])
                Utils.script_sleep(1)
                continue

    @property
    def need_to_retire(self):
        """Checks whether the script needs to retire ships

        Returns:
            bool: True if the script needs to retire ships
        """
        # check if it has already retired with current combat count so it doesn't enter a loop
        if self.config.combat['enabled'] and self.stats.combat_done > self.last_retire:
            return self.stats.combat_done % self.config.combat['retire_cycle'] == 0
