from util.logger import Logger
from util.utils import Utils, Region


class EnhancementModule(object):

    def __init__(self, config, stats):
        """Initializes the Enhancement module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.config = config
        self.stats = stats
        self.sorted = False
        self.called_from_menu = False
        self.enhancement_done = False
        self.previous_call_place = "combat"
        self.fill_count = 0
        self.last_enhance = 0
        self.region = {
            'combat_enhance_button': Region(1150, 750, 215, 64),
            'button_favorite': Region(1014, 19, 170, 42),
            'button_go_back': Region(54, 57, 67, 67),
            'dock_tab': Region(297, 1015, 155, 40),
            'sort_filters_button': Region(1655, 14, 130, 51),
            'rarity_all_ship_filter': Region(435, 668, 190, 45),
            'extra_all_ship_filter': Region(435, 779, 190, 45),
            'extra_enhanceable_ship_filter': Region(1143, 779, 190, 45),
            'confirm_filter_button': Region(1090, 933, 220, 60),
            'first_favorite_ship': Region(209, 209, 80, 120),
            'fill_button': Region(1467, 917, 140, 38),
            'enhance_tab_normal_ship': Region(31, 188, 91, 91),
            'enhance_tab_retro_ship': Region(31, 329, 91, 91),
            'enhance_orange_button': Region(1705, 916, 167, 40),
            'confirm_selected_equipment_button': Region(1320, 785, 232, 62),
            'disassemble_button': Region(1099, 827, 225, 58),
            'tap_to_continue': Region(661, 840, 598, 203)
        }

    def enhancement_logic_wrapper(self, forced=False):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of enhancing a ship.

        Args:
            forced (bool): Forces enhancement to start even if need_to_enhance returns False.
        
        Returns:
            enhancement_done (bool): whether at least one enhancement was completed.
        """
        if self.need_to_enhance or forced:
            self.last_enhance = self.stats.combat_done
            self.fill_count = 0
            self.called_from_menu = False
            self.enhancement_done = False
            Logger.log_msg("Opening dock to enhance ship.")

            while True:
                Utils.update_screen()
                if Utils.find("menu/button_sort"):
                    # Tap enhace button from dock is full alert
                    Utils.touch_randomly(self.region['combat_enhance_button'])
                    Utils.script_sleep(3)
                    continue
                if Utils.find("menu/button_battle"):
                    Utils.touch_randomly(self.region['dock_tab'])
                    self.called_from_menu = True
                    Utils.script_sleep(2)
                    continue
                if Utils.find("retirement/empty"):
                    Logger.log_msg("No ships left to enhance.")
                    Utils.touch_randomly(self.region['button_favorite'])
                    Utils.script_sleep(0.5)
                    if self.called_from_menu:
                        Utils.menu_navigate("menu/button_battle")
                    else:
                        Utils.touch_randomly(self.region['button_go_back'])
                    return self.enhancement_done
                if Utils.find("enhancement/button_favorite", 0.99):
                    self.enhance_ship()
                    Utils.script_sleep(1)
                    Utils.touch_randomly(self.region['button_favorite'])
                    Utils.script_sleep(0.5)
                    if self.called_from_menu:
                        self.previous_call_place = "menu"
                        Utils.menu_navigate("menu/button_battle")
                    else:
                        self.previous_call_place = "combat"
                        Utils.touch_randomly(self.region['button_go_back'])
                    return self.enhancement_done
                if Utils.find("menu/dock"):
                    Utils.touch_randomly(self.region['button_favorite'])
                    Utils.script_sleep(1)
                    self.set_sort()
                    continue
                else:
                    Utils.touch_randomly(self.region['button_go_back'])
                    Utils.script_sleep(2)
    
    def set_sort(self):
        """Method which sets the correct filters for enhancement, i.e. 'Enhanceable' option.
        """
        if self.config.retirement['enabled'] and (self.previous_call_place == "combat" or not self.called_from_menu):
            # Reset self.sorted if the request to enhance came from combat
            # this time or the previous time. The check is necessary because
            # the filters for enhancement and retirement in combat are shared.
            # If the alert "dock is full" is encountered, the enhancement 
            # module is called without doubts even if it ends up not enhancing
            # (e.g. no common ships unlocked in dock).
            self.sorted = False
        while not self.sorted:
            Logger.log_debug("Enhancement: Opening sorting menu.")
            Utils.touch_randomly(self.region['sort_filters_button'])
            Utils.script_sleep(0.5)
            # Touch the All button to clear any current filter
            Utils.touch_randomly(self.region['rarity_all_ship_filter'])
            Utils.script_sleep(0.5)
            Utils.touch_randomly(self.region['extra_all_ship_filter'])
            Utils.script_sleep(0.5)
            # Touch the Enhanceable button
            Utils.touch_randomly(self.region['extra_enhanceable_ship_filter'])
            Utils.script_sleep(0.5)
            
            # check if correct options are enabled
            # get the regions of enabled options
            options = Utils.get_enabled_ship_filters(filter_categories="rarity;extra")
            if len(options) == 0:
                # if the list is empty it probably means that there was an ui update
                # pausing and requesting for user confirmation
                Logger.log_error("No options detected. User's input required.")
                input("Manually fix sorting options. Press Enter to continue...")
                self.sorted = True
            else:
                checks = [False, False]
                for option in options:
                    # tolerance is set to 25 since the regions chosen for tapping are smaller than the actual ones
                    if self.region['rarity_all_ship_filter'].equal_approximated(option, 25):
                        Logger.log_debug("Enhancement: Rarity All option enabled")
                        checks[0] = True
                    if self.region['extra_enhanceable_ship_filter'].equal_approximated(option, 25):
                        Logger.log_debug("Enhancement: Enhanceable option enabled")
                        checks[1] = True
                if checks[0] and checks[1]:
                    Logger.log_debug("Enhancement: Sorting options confirmed")
                    self.sorted = True
            Utils.touch_randomly(self.region['confirm_filter_button'])
            Utils.script_sleep(1)

    def enhance_ship(self):
        """
        Method that selects the first (leftmost of the first row) favorite ship and proceeds to enhance her.
        """

        #selects ship
        Utils.touch_randomly(self.region['first_favorite_ship'])
        Utils.script_sleep(1)

        while True:
            Utils.update_screen()

            if Utils.find("enhancement/menu_enhance"):
                Logger.log_debug("Filling with ships.")
                self.fill_count += 1
                #taps the "fill" button
                Utils.touch_randomly(self.region['fill_button'])
                Utils.update_screen()
            if Utils.find("enhancement/alert_no_items", 0.85) or self.fill_count >= 10:
                Logger.log_warning("Not enough ships to enhance.")
                break
            if Utils.find("enhancement/menu_level", 0.8):
                self.handle_retirement()
                Logger.log_msg("Successfully enhanced ship.")
                if self.config.enhancement['single_enhancement'] or self.fill_count >= 10:
                    break
                continue
            if Utils.find("enhancement/menu_details"):
                Logger.log_debug("Opening enhance menu.")
                if not Utils.find("enhancement/menu_retrofit", 0.9):
                    Utils.touch_randomly(self.region['enhance_tab_normal_ship'])
                else:
                    Utils.touch_randomly(self.region['enhance_tab_retro_ship'])
                continue

        Utils.touch_randomly(self.region['button_go_back'])
        Utils.script_sleep(1)
        return

    def handle_retirement(self):
        """
        Method that handles the disassembling of the ship materials used in the enhancement process.
        """

        #tap the "enhance" button
        Utils.touch_randomly(self.region['enhance_orange_button'])
        #the enhanced alert lasts about three seconds, so there's enough time to catch it
        #even if the scripts sleeps for a little bit. This pause ensures the script does not take
        #the screenshot before the alert is shown.
        Utils.script_sleep(0.5)
        Utils.update_screen()

        if not Utils.find("enhancement/alert_enhanced", 0.85):
            Logger.log_debug("Didn't find enhanced alert.")
            return
        else:
            Logger.log_debug("Successfully enhanced ship.")
            self.enhancement_done = True

        while True:
            Utils.update_screen()

            if Utils.find("menu/alert_info"):
                Utils.touch_randomly(self.region['confirm_selected_equipment_button'])
                Utils.script_sleep(1)
                continue
            if Utils.find("retirement/button_disassemble"):
                Utils.touch_randomly(self.region['disassemble_button'])
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(self.region['tap_to_continue'])
                Utils.script_sleep(1)
                return

    @property
    def need_to_enhance(self):
        """Checks whether the script needs to retire ships

        Returns:
            bool: True if the script needs to retire ships
        """
        # check if it has already retired with current combat count so it doesn't enter a loop
        if self.config.combat['enabled'] and self.stats.combat_done > self.last_enhance:
            return self.stats.combat_done % self.config.combat['retire_cycle'] == 0
        else:
            return False
