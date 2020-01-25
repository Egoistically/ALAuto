from util.logger import Logger
from util.utils import Utils, Region


class EventModule(object):

    def __init__(self, config, stats):
        """Initializes the Enhancement module.

        Args:
            config (Config): ALAuto Config instance
            stats (Stats): ALAuto stats instance
        """
        self.config = config
        self.stats = stats
        self.last_enhance = 0
        self.levels = config.events['levels']
        self.finished = False
        self.region = {
            'menu_fleet_go': Region(1485, 872, 270, 74),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'tap_to_continue': Region(661, 840, 598, 203),
            'dismiss_combat_finished': Region(725, 965, 647, 76),
            'combat_end_confirm': Region(1520, 963, 216, 58),
            'close_info_dialog': Region(1319, 217, 47, 47),
            'combat_dismiss_surface_fleet_summary': Region(790, 950, 250, 65),
            'combat_button_no': Region(689, 757, 93, 46),

            'crosswave_ex': Region(1718, 246, 75, 75),
            'crosswave_hard': Region(1650, 449, 75, 75),
            'crosswave_normal': Region(1752, 612, 75, 75),
            'crosswave_easy': Region(1683, 798, 75, 75),

            'royal_maids_ex': Region(1583, 218, 165, 42),
            'royal_maids_hard': Region(1645, 366, 160, 30),
            'royal_maids_normal': Region(1587, 533, 160, 30),
            'royal_maids_easy': Region(1634, 699, 160, 30)
        }

    def event_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of completing an event
        """
        event = self.config.events['name']
        events = ['Crosswave', 'Royal_Maids']

        if event in events and not self.finished:
            Logger.log_msg("Opening event menu.")

            while not Utils.find("menu/operation"):
                Utils.find_and_touch(f"event/{event}/menu_button")
                Utils.wait_update_screen(1)

            Logger.log_msg("Event levels: " + str(self.levels))

            while ('EX' in self.levels):
                Utils.wait_update_screen(1)
                if Utils.find(f"event/{event}/ex_completed", 0.99):
                    Logger.log_info("No more EX combats to do.")
                    break

                Utils.touch_randomly(self.region[f'{event.lower()}_ex'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg(f"Finished EX {event.replace('_', ' ')} combat.")
            while ('H' in self.levels):
                Utils.wait_update_screen(1)
                if Utils.find(f"event/{event}/hard_completed") and not self.config.events['ignore_rateup']:
                    Logger.log_info("No more Hard combats to do.")
                    break

                Utils.touch_randomly(self.region[f'{event.lower()}_hard'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg(f"Finished Hard {event.replace('_', ' ')} combat.")
            while ('N' in self.levels):
                Utils.wait_update_screen(1)
                if Utils.find(f"event/{event}/normal_completed") and not self.config.events['ignore_rateup']:
                    Logger.log_info("No more Normal combats to do.")
                    break

                Utils.touch_randomly(self.region[f'{event.lower()}_normal'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg(f"Finished Normal {event.replace('_', ' ')} combat.")
            while ('E' in self.levels):
                Utils.wait_update_screen(1)
                if Utils.find(f"event/{event}/easy_completed") and not self.config.events['ignore_rateup']:
                    Logger.log_info("No more Easy combats to do.")
                    break

                Utils.touch_randomly(self.region[f'{event.lower()}_easy'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg(f"Finished Easy {event.replace('_', ' ')} combat.")

            Logger.log_msg("Finished all event combats, going back to menu.")

            Utils.menu_navigate("menu/button_battle")
            self.finished = True
            return

    def pre_combat_handler(self):
        """Handles pre-combat stuff like fleet selection and starts combat_handler function.
        """
        while True:
            Utils.wait_update_screen(1)

            if Utils.find("combat/menu_select_fleet"):
                Logger.log_debug("Found event fleet go button.")
                Utils.touch_randomly(self.region['menu_fleet_go'])
                continue
            if Utils.find("menu/alert_close"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                continue
            if Utils.find("combat/menu_formation"):
                Logger.log_debug("Found formation asset.")
                return True

    def combat_handler(self):
        Logger.log_msg("Starting combat.")
        Utils.touch_randomly(self.region['menu_combat_start'])
        Utils.script_sleep(4)

        while True:
            Utils.wait_update_screen(1)

            if Utils.find("event/button_no"):
                Utils.touch_randomly(self.region['combat_button_no'])
                Utils.script_sleep(1)
                continue
            if Utils.find("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
                Utils.script_sleep(5)
                continue
            if Utils.find("combat/menu_touch2continue"):
                Utils.touch_randomly(self.region['tap_to_continue'])
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(self.region['tap_to_continue'])
                Utils.script_sleep(1)
                continue
            if Utils.find("combat/button_confirm"):
                Logger.log_msg("Combat ended.")
                Utils.touch_randomly(self.region['combat_end_confirm'])
                self.stats.increment_combat_done()
                Utils.script_sleep(1)
                return
            if Utils.find("combat/commander"):
                # prevents fleet with submarines from getting stuck at combat end screen
                Utils.touch_randomly(self.region["combat_dismiss_surface_fleet_summary"])
                Utils.script_sleep(1)
                continue
            if Utils.find("combat/menu_combat_finished"):
                Utils.touch_randomly(self.region['dismiss_combat_finished'])
                Utils.script_sleep(1)
                continue