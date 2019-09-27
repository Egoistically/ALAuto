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
        self.last_enhance = 0
        self.region = {
            'button_favorite': Region(1014, 19, 170, 42)
        }

    def enhancement_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action enhancing a ship
        """
        if self.need_to_enhance:
            self.last_enhance = self.stats.combat_done
            Logger.log_msg("Opening dock to enhance ship.")

            while True:
                Utils.update_screen()
                
                if Utils.find("menu/button_battle"):
                    Utils.touch_randomly(Region(297, 1015, 155, 40))
                    Utils.script_sleep(1)
                    continue
                if Utils.find("enhancement/button_favorite", 0.99):
                    self.enhance_ship()
                    Utils.touch_randomly(self.region['button_favorite'])
                    Utils.touch_randomly(Region(54, 57, 67, 67))
                    return
                if Utils.find("menu/dock"):
                    Utils.touch_randomly(self.region['button_favorite'])
                    continue

    def enhance_ship(self):
        Utils.touch_randomly(Region(209, 209, 80, 120))
        Utils.script_sleep(1)

        while True:
            Utils.update_screen()

            if Utils.find("enhancement/menu_enhance"):
                Logger.log_debug("Filling with ships.")
                Utils.touch_randomly(Region(1467, 917, 140, 38))
                Utils.update_screen()
            if Utils.find("enhancement/alert_no_items", 0.85):
                Logger.log_warning("Not enough ships to enhance.")
                break
            if Utils.find("enhancement/menu_level", 0.8):
                self.handle_retirement()
                Logger.log_msg("Successfully finished enhancing.")
                break
            if Utils.find("enhancement/menu_details"):
                Logger.log_debug("Opening enhance menu.")
                Utils.touch_randomly(Region(31, 188, 91, 91))
                continue

        Utils.touch_randomly(Region(54, 57, 67, 67))
        Utils.script_sleep(1)
        return

    def handle_retirement(self):
        Utils.touch_randomly(Region(1705, 916, 167, 40))
        Utils.update_screen()

        if not Utils.find("enhancement/alert_enhanced", 0.85):
            Logger.log_debug("Didn't find enhanced alert.")
            return
        else:
            Logger.log_debug("Successfully enhanced ship.")

        while True:
            Utils.update_screen()

            if Utils.find("menu/alert_info"):
                Utils.touch_randomly(Region(1320, 785, 232, 62))
                Utils.script_sleep(1)
                continue
            if Utils.find("retirement/button_disassemble"):
                Utils.touch_randomly(Region(1099, 827, 225, 58))
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                Utils.script_sleep(1)
                return

    @property
    def need_to_enhance(self):
        """Checks whether the script needs to retire ships

        Returns:
            bool: True if the script needs to retire ships
        """
        # check if it has already retired with current combat count so it doesn't enter a loop
        if self.stats.combat_done > self.last_enhance:
            return self.stats.combat_done % int(self.config.combat['retire_cycle']) == 0