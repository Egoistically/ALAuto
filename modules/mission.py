from util.utils import Utils, Region
from util.logger import Logger


class MissionModule(object):
    def __init__(self, config, stats):
        """Initializes the Expedition module.
        Args:
            config (Config): kcauto Config instance
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.region = {
            'mission_menu': Region(1206, 1001, 220, 64),
            'collect': Region(1551, 0, 111, 58),
            'first_claim': Region(1646, 174, 117, 102),
            'button_back': Region(48, 43, 76, 76),
            'tap_to_continue': Region(661, 840, 598, 203),
            'dismiss_ship_drop': Region(1228, 103, 692, 735)
        }

    def mission_logic_wrapper(self):
        while True:
            Utils.update_screen()

            if Utils.find("mission/alert_completed"):
                Logger.log_msg("Found mission completed alert.")
                Utils.touch_randomly(self.region["mission_menu"])
                continue
            if Utils.find("menu/drop_ssr"):
                Logger.log_msg("Received SSR ship as reward.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                continue
            if Utils.find("menu/drop_elite"):
                Logger.log_msg("Received ELITE ship as reward.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                continue
            while Utils.find("menu/missions"):
                Utils.update_screen()

                if Utils.find("mission/button_collect"):
                    Logger.log_msg("Collected all missions.")
                    Utils.touch_randomly(self.region["collect"])
                    Utils.script_sleep(3)
                    continue
                if Utils.find("mission/button_claim"):
                    Logger.log_msg("Claimed mission.")
                    Utils.touch_randomly(self.region["first_claim"])
                    continue
                if Utils.find("menu/item_found"):
                    Utils.touch_randomly(self.region["tap_to_continue"])
                    continue
                else:
                    Logger.log_msg("No more missions to claim/collect.")
                    Utils.menu_navigate("menu/button_battle")
                    return True