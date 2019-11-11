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
        self.levels = config.events['levels'].split(',')
        self.finished = False
        self.region = {
            'menu_fleet_go': Region(1485, 872, 270, 74),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'crosswave_ex': Region(1718, 246, 75, 75),
            'crosswave_hard': Region(1650, 449, 75, 75),
            'crosswave_normal': Region(1752, 612, 75, 75),
            'crosswave_easy': Region(1683, 798, 75, 75),
            'tap_to_continue': Region(661, 840, 598, 203),
            'dismiss_combat_finished': Region(725, 965, 647, 76),
            'combat_end_confirm': Region(1520, 963, 216, 58)
        }

    def event_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of completing an event
        """
        if self.config.events['name'] == 'Crosswave' and not self.finished:
            Logger.log_msg("Opening event menu.")

            while not Utils.find("menu/operation"):
                Utils.find_and_touch("event/crosswave/menu_button")
                Utils.wait_update_screen(1)

            Logger.log_msg("Event levels: " + str(self.levels))

            while ('EX' in self.levels):
                Utils.update_screen()
                if Utils.find("event/crosswave/ex_completed", 0.98):
                    Logger.log_info("No more EX combats to do.")
                    break

                Utils.touch_randomly(self.region['crosswave_ex'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg("Finished EX crosswave combat.")
            while ('H' in self.levels):
                Utils.update_screen()
                if Utils.find("event/crosswave/hard_completed"):
                    Logger.log_info("No more hard combats to do.")
                    break

                Utils.touch_randomly(self.region['crosswave_hard'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg("Finished hard crosswave combat.")
            while ('N' in self.levels):
                Utils.update_screen()
                if Utils.find("event/crosswave/normal_completed"):
                    Logger.log_info("No more normal combats to do.")
                    break

                Utils.touch_randomly(self.region['crosswave_normal'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg("Finished normal crosswave combat.")
            while ('E' in self.levels):
                Utils.update_screen()
                if Utils.find("event/crosswave/easy_completed"):
                    Logger.log_info("No more easy combats to do.")
                    break

                Utils.touch_randomly(self.region['crosswave_easy'])
                if self.pre_combat_handler():
                    self.combat_handler()
                    Logger.log_msg("Finished easy crosswave combat.")

            Logger.log_msg("Finished all event combats, going back to menu.")

            Utils.menu_navigate("menu/button_battle")
            self.finished = True
            return

    def pre_combat_handler(self):
        """Handles pre-combat stuff like fleet selection and starts combat_handler function.
        """
        while True:
            Utils.update_screen()

            if Utils.find("combat/menu_select_fleet"):
                Logger.log_debug("Found event fleet go button.")
                Utils.touch_randomly(self.region['menu_fleet_go'])
                continue
            if Utils.find("combat/menu_formation"):
                Logger.log_debug("Found formation asset.")
                return True

    def combat_handler(self):
        Logger.log_msg("Starting combat.")
        Utils.touch_randomly(self.region['menu_combat_start'])
        Utils.script_sleep(4)

        while True:
            Utils.update_screen()

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
                Utils.script_sleep(1)
                return
            if Utils.find("combat/menu_combat_finished"):
                Utils.touch_randomly(self.region['dismiss_combat_finished'])
                Utils.script_sleep(1)
                continue