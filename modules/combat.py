import math
import string
from util.logger import Logger
from util.utils import Region, Utils
from scipy import spatial
from threading import Thread

class CombatModule(object):

    def __init__(self, config, stats):
        """Initializes the Combat module.

        Args:
            config (Config): ALAuto Config instance.
            stats (Stats): ALAuto Stats instance.
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.chapter_map = self.config.combat['map']
        Utils.small_boss_icon = config.combat['small_boss_icon']
        self.exit = 0
        self.combats_done = 0
        self.enemies_list = []
        self.mystery_nodes_list = []
        self.blacklist = []
        self.movement_event = {}

        self.kills_count = 0
        self.kills_before_boss = {
            '1-1': 1, '1-2': 2, '1-3': 2, '1-4': 3,
            '2-1': 2, '2-2': 3, '2-3': 3, '2-4': 3,
            '3-1': 3, '3-2': 3, '3-3': 3, '3-4': 3,
            '4-1': 3, '4-2': 3, '4-3': 3, '4-4': 4,
            '5-1': 4, '5-2': 4, '5-3': 4, '5-4': 4,
            '6-1': 4, '6-2': 4, '6-3': 4, '6-4': 5,
            '7-1': 5, '7-2': 5, '7-3': 5, '7-4': 5,
            '8-1': 4, '8-2': 4, '8-3': 4, '8-4': 4,
            '9-1': 5, '9-2': 5, '9-3': 5, '9-4': 5,
            '10-1': 6, '10-2': 6, '10-3': 6, '10-4': 6,
            '11-1': 6, '11-2': 6, '11-3': 6, '11-4': 6,
            '12-1': 6, '12-2': 6, '12-3': 6, '12-4': 6,
            '13-1': 6, '13-2': 6, '13-3': 6, '13-4': 7
        }
        if self.chapter_map not in self.kills_before_boss:
            # check if current map is present in the dictionary and if it isn't,
            # a new entry is added with kills_before_boss value
            self.kills_before_boss[self.chapter_map] = self.config.combat['kills_before_boss']
        elif self.config.combat['kills_before_boss'] != 0:
            # updates default value with the one provided by the user
            self.kills_before_boss[self.chapter_map] = self.config.combat['kills_before_boss']

        self.region = {
            'fleet_lock': Region(1790, 750, 130, 30),
            'open_strategy_menu': Region(1797, 617, 105, 90),
            'disable_subs_hunting_radius': Region(1655, 615, 108, 108),
            'close_strategy_menu': Region(1590, 615, 40, 105),
            'menu_button_battle': Region(1517, 442, 209, 206),
            'map_summary_go': Region(1289, 743, 280, 79),
            'fleet_menu_go': Region(1485, 872, 270, 74),
            'combat_ambush_evade': Region(1493, 682, 208, 56),
            'combat_com_confirm': Region(848, 740, 224, 56),
            'combat_end_confirm': Region(1520, 963, 216, 58),
            'combat_dismiss_surface_fleet_summary': Region(790, 950, 250, 65),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'tap_to_continue': Region(661, 840, 598, 203),
            'close_info_dialog': Region(1326, 274, 35, 35),
            'dismiss_ship_drop': Region(1228, 103, 692, 735),
            'retreat_button': Region(1130, 985, 243, 60),
            'dismiss_commission_dialog': Region(1065, 732, 235, 68),
            'normal_mode_button': Region(88, 990, 80, 40),
            'map_nav_right': Region(1831, 547, 26, 26),
            'map_nav_left': Region(65, 547, 26, 26),
            'event_button': Region(1770, 250, 75, 75),
            'lock_ship_button': Region(1086, 739, 200, 55),
            'clear_second_fleet': Region(1690, 473, 40, 40),
            'button_switch_fleet': Region(1430, 985, 240, 60),
            'menu_nav_back': Region(54, 57, 67, 67)
        }

        self.swipe_counter = 0

    def combat_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of sortieing combat fleets and resolving combat.

        Returns:
            int: 1 if boss was defeated, 2 if morale is too low and 3 if dock is full.
        """
        self.exit = 0
        self.combats_done = 0
        self.kills_count = 0
        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()
        self.swipe_counter = 0

        while True:
            Utils.wait_update_screen()

            if Utils.find("menu/button_sort"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 3
            if Utils.find("combat/alert_morale_low"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 2
                break
            if Utils.find("menu/button_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("menu/button_battle"):
                Logger.log_debug("Found menu battle button.")
                Utils.touch_randomly(self.region["menu_button_battle"])
                Utils.wait_update_screen(1)
                continue
            if Utils.find("combat/menu_fleet") and (lambda x:x > 414 and x < 584)(Utils.find("combat/menu_fleet").y) and not self.config.combat['boss_fleet']:
                if not self.chapter_map[0].isdigit() and string.ascii_uppercase.index(self.chapter_map[2:3]) < 1 or self.chapter_map[0].isdigit():
                    Logger.log_msg("Removing second fleet from fleet selection.")
                    Utils.touch_randomly(self.region["clear_second_fleet"])
            if Utils.find("combat/menu_select_fleet"):
                Logger.log_debug("Found fleet select go button.")
                Utils.touch_randomly(self.region["fleet_menu_go"])
                Utils.script_sleep(1)
                continue
            if Utils.find("combat/button_go"):
                Logger.log_debug("Found map summary go button.")
                Utils.touch_randomly(self.region["map_summary_go"])
                continue
            if Utils.find("combat/button_retreat"):
                Logger.log_debug("Found retreat button, starting clear function.")
                if not self.clear_map():
                    self.stats.increment_combat_attempted()
                    break
            if self.exit == 1 or self.exit == 5:
                self.stats.increment_combat_done()
                break
            if self.exit > 1:
                self.stats.increment_combat_attempted()
                break
            if Utils.find("menu/button_normal_mode") and self.chapter_map[0].isdigit():
                Logger.log_debug("Disabling hard mode.")
                Utils.touch_randomly(self.region['normal_mode_button'])
                Utils.wait_update_screen(1)
            if Utils.find_and_touch('maps/map_{}'.format(self.chapter_map), 0.99):
                Logger.log_msg("Found specified map.")
                continue
            else:
                self.reach_map()
                continue

        Utils.script_sleep(1)
        Utils.menu_navigate("menu/button_battle")

        return self.exit

    def reach_map(self):
        """
        Method to move to the world where the specified map is located.
        Only works with worlds added to assets (from 1 to 8) and some event maps.
        Also checks if hard mode is enabled.
        """
        _map = 0

        if not self.chapter_map[0].isdigit():
            letter = self.chapter_map[2:3]
            event_maps = ['A', 'B', 'S', 'C', 'D']

            Utils.touch_randomly(self.region['event_button'])
            Utils.wait_update_screen(1)

            if event_maps.index(letter) < 3 and Utils.find("menu/button_normal_mode", 0.8) or \
               event_maps.index(letter) > 2 and not Utils.find("menu/button_normal_mode", 0.8):
                Utils.touch_randomly(self.region['normal_mode_button'])
                Utils.wait_update_screen(1)
        else:
            for x in range(1, 14):
                if Utils.find("maps/map_{}-1".format(x), 0.99):
                    _map = x
                    break

            if _map != 0:
                taps = int(self.chapter_map.split("-")[0]) - _map
                for x in range(0, abs(taps)):
                    if taps >= 1:
                        Utils.touch_randomly(self.region['map_nav_right'])
                        Logger.log_debug("Swiping to the right")
                        Utils.wait_update_screen()
                    else:
                        Utils.touch_randomly(self.region['map_nav_left'])
                        Logger.log_debug("Swiping to the left")
                        Utils.wait_update_screen()

        if Utils.find('maps/map_{}'.format(self.chapter_map), 0.99):
            Logger.log_msg("Successfully reached the world where map is located.")
        else:
            Logger.log_error("Cannot find the specified map, please move to the world where it's located.")
            while not Utils.find('maps/map_{}'.format(self.chapter_map), 0.99):
                Utils.wait_update_screen(1)

    def battle_handler(self, boss=False):
        Logger.log_msg("Starting combat.")

        while not (Utils.find("combat/menu_loading", 0.8)):
            Utils.update_screen()

            if Utils.find("combat/alert_morale_low") or Utils.find("menu/button_sort"):
                self.retreat_handler()
                return False
            elif Utils.find("combat/combat_pause", 0.7):
                Logger.log_warning("Loading screen was not found but combat pause is present, assuming combat is initiated normally.")
                break
            else:
                Utils.touch_randomly(self.region["menu_combat_start"])
                Utils.script_sleep(1)

        Utils.script_sleep(4)

        while True:
            Utils.update_screen()

            if Utils.find("combat/alert_lock"):
                Logger.log_msg("Locking received ship.")
                Utils.touch_randomly(self.region['lock_ship_button'])
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
            if Utils.find("menu/drop_ssr"):
                Logger.log_msg("Received SSR ship as drop.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/drop_elite"):
                Logger.log_msg("Received ELITE ship as drop.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/drop_rare"):
                Logger.log_msg("Received new RARE ship as drop.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/drop_common"):
                Logger.log_msg("Received new COMMON ship as drop.")
                Utils.touch_randomly(self.region['dismiss_ship_drop'])
                Utils.script_sleep(1)
                continue
            if Utils.find("combat/button_confirm"):
                Logger.log_msg("Combat ended.")
                self.kills_count += 1
                Utils.touch_randomly(self.region["combat_end_confirm"])
                Utils.script_sleep(1)
                if boss:
                    return True
                Utils.update_screen()
            if Utils.find("combat/alert_unable_battle"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                Utils.script_sleep(3)
                self.exit = 4
                return
            if Utils.find("menu/button_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("combat/button_retreat"):
                Utils.script_sleep(3)
                self.combats_done += 1
                #Utils.touch_randomly(self.region["hide_strat_menu"])
                return
            if Utils.find("combat/commander"):
                # prevents fleet with submarines from getting stuck at combat end screen
                Utils.touch_randomly(self.region["combat_dismiss_surface_fleet_summary"])
                continue

    def movement_handler(self, target_info):
        """
        Method that handles the fleet movement until it reach its target (mystery node or enemy node).
        If the coordinates are wrong, they will be blacklisted and another set of coordinates to work on is obtained.
        If the target is a mystery node and what is found is ammo, then the method will fall in the blacklist case
        and search for another enemy: this is inefficient and should be improved, but it works.

        Args:
            target_info (list): coordinate_x, coordinate_y, type. Describes the selected target.
        Returns:
            (int): 1 if a fight is needed, otherwise 0.
        """
        Logger.log_msg("Moving towards objective.")
        count = 0
        location = [target_info[0], target_info[1]]
        Utils.script_sleep(1)

        while True:
            Utils.update_screen()
            event = self.check_movement_threads()

            if event["combat/button_evade"]:
                Logger.log_msg("Ambush was found, trying to evade.")
                Utils.touch_randomly(self.region["combat_ambush_evade"])
                Utils.script_sleep(0.5)
                continue
            if event["combat/alert_failed_evade"]:
                Logger.log_warning("Failed to evade ambush.")
                self.kills_count -= 1
                Utils.touch_randomly(self.region["menu_combat_start"])
                self.battle_handler()
                continue
            if event["menu/item_found"]:
                Logger.log_msg("Item found on node.")
                Utils.touch_randomly(self.region['tap_to_continue'])
                if Utils.find("combat/menu_emergency"):
                    Utils.script_sleep(1)
                    #Utils.touch_randomly(self.region["hide_strat_menu"])
                if target_info[2] == "mystery_node":
                    Logger.log_msg("Target reached.")
                    return 0
                continue
            if event["menu/alert_info"]:
                Logger.log_debug("Found alert.")
                Utils.find_and_touch("menu/alert_close")
                continue
            if event["combat/menu_loading"]:
                return 1
            elif event["combat/menu_formation"]:
                Utils.find_and_touch("combat/auto_combat_off")
                return 1
            else:
                if count != 0 and count % 3 == 0:
                    Utils.touch(location)
                if count > 21:
                    Logger.log_msg("Blacklisting location and searching for another enemy.")
                    self.blacklist.append(location[0:2])

                    location = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))
                    count = 0
                count += 1

    def unable_handler(self, coords):
        """
        Method called when the path to the boss fleet is obstructed by mobs: it procedes to switch targets to the mobs
        which are blocking the path.

        Args:
            coords (list): coordinate_x, coordinate_y. These coordinates describe the boss location.
        """
        Logger.log_debug("Unable to reach boss function started.")
        self.blacklist.clear()
        closest_to_boss = self.get_closest_target(self.blacklist, coords)

        Utils.touch(closest_to_boss)
        Utils.wait_update_screen(1)

        if Utils.find("combat/alert_unable_reach"):
            Logger.log_warning("Unable to reach next to boss.")
            self.blacklist.append(closest_to_boss[0:2])

            while True:
                closest_enemy = self.get_closest_target(self.blacklist)
                Utils.touch(closest_enemy)
                Utils.update_screen()

                if Utils.find("combat/alert_unable_reach"):
                    self.blacklist.append(closest_enemy[0:2])
                else:
                    break

            self.movement_handler(closest_enemy)
            if not self.battle_handler():
                return False
            return True
        else:
            self.movement_handler(closest_to_boss)
            if not self.battle_handler():
                return False
            return True

    def retreat_handler(self):
        """ Retreats if necessary.
        """
        while True:
            Utils.wait_update_screen(2)

            if Utils.find("combat/alert_morale_low"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 2
                continue
            if Utils.find("menu/button_sort"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 3
                continue
            if Utils.find("combat/menu_formation"):
                Utils.touch_randomly(self.region["menu_nav_back"])
                continue
            if Utils.find("combat/button_retreat"):
                Utils.touch_randomly(self.region['retreat_button'])
                continue
            if Utils.find("menu/button_confirm"):
                Utils.touch_randomly(self.region['dismiss_commission_dialog'])
                continue
            if Utils.find("menu/attack"):
                if self.exit != 1 and self.exit != 4 and self.exit != 5:
                    Logger.log_msg("Retreating...")
                return

    def clear_map(self):
        """ Clears map.
        """
        Logger.log_msg("Started map clear.")
        Utils.script_sleep(2.5)

        while Utils.find("combat/fleet_lock", 0.99):
            Utils.touch_randomly(self.region["fleet_lock"])
            Logger.log_warning("Fleet lock is not supported, disabling it.")
            Utils.wait_update_screen()

        #swipe map to fit everything on screen
        swipes = {
            'E-C3': lambda: Utils.swipe(960, 800, 960, 400, 300),
            'E-A3': lambda: Utils.swipe(960, 800, 960, 400, 300),
            'E-B3': lambda: Utils.swipe(960, 540, 1000, 620, 300),
            'E-D3': lambda: Utils.swipe(960, 540, 1000, 620, 300),
            'E-SP5': lambda: Utils.swipe(350, 500, 960, 800, 300),
            '7-2': lambda: Utils.swipe(960, 540, 1300, 600, 300),
            '12-2': lambda: Utils.swipe(1000, 570, 1300, 540, 300),
            '12-3': lambda: Utils.swipe(1250, 530, 1300, 540, 300),
            '12-4': lambda: Utils.swipe(960, 300, 960, 540, 300),
            '13-1': lambda: Utils.swipe(1020, 500, 1300, 540, 300),
            '13-2': lambda: Utils.swipe(1125, 550, 1300, 540, 300),
            '13-3': lambda: Utils.swipe(1150, 510, 1300, 540, 300),
            '13-4': lambda: Utils.swipe(1200, 450, 1300, 540, 300)
        }
        swipes.get(self.chapter_map, lambda: Utils.swipe(960, 540, 1300, 540, 300))()

        # disable subs' hunting range
        if self.config.combat["hide_subs_hunting_range"]:
            Utils.script_sleep(0.5)
            Utils.touch_randomly(self.region["open_strategy_menu"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["disable_subs_hunting_radius"])
            Utils.script_sleep()
            Utils.touch_randomly(self.region["close_strategy_menu"])

        target_info = self.get_closest_target(self.blacklist)

        while True:
            Utils.update_screen()

            if Utils.find("combat/alert_unable_battle"):
                Utils.touch_randomly(self.region['close_info_dialog'])
                self.exit = 4
            if self.config.combat['retreat_after'] != 0 and self.combats_done >= self.config.combat['retreat_after']:
                Logger.log_msg("Retreating after defeating {} enemies".format(self.config.combat['retreat_after']))
                self.exit = 5
            if self.exit != 0:
                self.retreat_handler()
                return True
            if self.kills_count >= self.kills_before_boss[self.chapter_map] and Utils.find_in_scaling_range("enemy/fleet_boss"):
                Logger.log_msg("Boss fleet was found.")

                if self.config.combat['boss_fleet']:
                    s = 0
                    swipes = {
                        0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                        1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                        2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                        3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                    }

                    Utils.touch_randomly(self.region['button_switch_fleet'])
                    Utils.wait_update_screen(2)
                    boss_region = Utils.find_in_scaling_range("enemy/fleet_boss")

                    while not boss_region:
                        if s > 3: s = 0
                        swipes.get(s)()

                        Utils.wait_update_screen(0.5)
                        boss_region = Utils.find_in_scaling_range("enemy/fleet_boss")
                        s += 1
                    Utils.swipe(boss_region.x, boss_region.y, 960, 540, 300)
                    Utils.wait_update_screen()

                boss_region = Utils.find_in_scaling_range("enemy/fleet_boss")
                #extrapolates boss_info(x,y,enemy_type) from the boss_region found
                boss_info = [boss_region.x + 50, boss_region.y + 25, "boss"]
                self.clear_boss(boss_info)
                continue
            if target_info == None:
                target_info = self.get_closest_target(self.blacklist, mystery_node=(not self.config.combat["ignore_mystery_nodes"]))
            if target_info:
                #tap at target's coordinates
                Utils.touch(target_info[0:2])
                Utils.update_screen()
            else:
                continue
            if Utils.find("combat/alert_unable_reach", 0.8):
                Logger.log_warning("Unable to reach the target.")
                self.blacklist.append(target_info[0:2])
                target_info = None
                continue
            else:
                movement_result = self.movement_handler(target_info)
                if movement_result == 1:
                    self.battle_handler()
                target_info = None

                self.blacklist.clear()
                continue

    def clear_boss(self, boss_info):
        Logger.log_debug("Started boss function.")

        self.enemies_list.clear()
        self.mystery_nodes_list.clear()
        self.blacklist.clear()

        while True:
            #tap at boss' coordinates
            Utils.touch(boss_info[0:2])
            Utils.update_screen()

            if Utils.find("combat/alert_unable_reach", 0.8):
                Logger.log_msg("Unable to reach boss.")
                #handle boss' coordinates
                if not self.unable_handler(boss_info[0:2]):
                    return
                continue
            else:
                self.movement_handler(boss_info)
                if self.battle_handler(boss=True):
                    self.exit = 1
                Utils.script_sleep(3)
                return

    def get_enemies(self, blacklist=[], boss=False):
        sim = 0.99
        filter_coordinates = True if len(self.enemies_list) == 0 else False
        if blacklist:
            Logger.log_info('Blacklist: ' + str(blacklist))
            if len(blacklist) > 2:
                self.enemies_list.clear()

        while not self.enemies_list:
            if (boss and len(blacklist) > 4) or (not boss and len(blacklist) > 3) or sim < 0.97:
                if self.swipe_counter > 3: self.swipe_counter = 0
                swipes = {
                    0: lambda: Utils.swipe(960, 240, 960, 940, 300),
                    1: lambda: Utils.swipe(1560, 540, 260, 540, 300),
                    2: lambda: Utils.swipe(960, 940, 960, 240, 300),
                    3: lambda: Utils.swipe(260, 540, 1560, 540, 300)
                }
                swipes.get(self.swipe_counter)()
                sim += 0.005
                self.swipe_counter += 1
            Utils.update_screen()

            l1 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] - 3, x[1] - 27], Utils.find_all('enemy/fleet_level', sim - 0.025, useMask=True)))
            l1 = [x for x in l1 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L1: " +str(l1))
            l2 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] + 75, x[1] + 110], Utils.find_all('enemy/fleet_1_down', sim - 0.02)))
            l2 = [x for x in l2 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L2: " +str(l2))
            l3 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] + 75, x[1] + 90], Utils.find_all('enemy/fleet_2_down', sim - 0.02)))
            l3 = [x for x in l3 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L3: " +str(l3))
            l4 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] + 75, x[1] + 125], Utils.find_all('enemy/fleet_3_up', sim - 0.035)))
            l4 = [x for x in l4 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L4: " +str(l4))
            l5 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] + 75, x[1] + 100], Utils.find_all('enemy/fleet_3_down', sim - 0.035)))
            l5 = [x for x in l5 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L5: " +str(l5))
            l6 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1770), map(lambda x:[x[0] + 75, x[1] + 110], Utils.find_all('enemy/fleet_2_up', sim - 0.025)))
            l6 = [x for x in l6 if (not self.filter_blacklist(x, blacklist))]
            Logger.log_debug("L6: " +str(l6))

            if self.config.combat['siren_elites']:
                l7 = Utils.find_siren_elites()
                l7 = [x for x in l7 if (not self.filter_blacklist(x, blacklist))]
                Logger.log_debug("L7: " +str(l7))
                self.enemies_list = l1 + l2 + l3 + l4 + l5 + l6 + l7
            else:
                self.enemies_list = l1 + l2 + l3 + l4 + l5 + l6
			
            sim -= 0.005

        if filter_coordinates:
            self.enemies_list = Utils.filter_similar_coords(self.enemies_list)
        return self.enemies_list

    def get_mystery_nodes(self, blacklist=[], boss=False):
        """Method which returns a list of mystery nodes' coordinates.
        """
        if len(blacklist) > 2:
            self.mystery_nodes_list.clear()
        
        if len(self.mystery_nodes_list) == 0 and not Utils.find('combat/question_mark', 0.9):
            # if list is empty and a question mark is NOT found
            return self.mystery_nodes_list
        else:
            # list has elements or list is empty but a question mark has been found
            filter_coordinates = True if len(self.mystery_nodes_list) == 0 else False
            sim = 0.95

            while not self.mystery_nodes_list and sim > 0.93:
                Utils.update_screen()

                l1 = filter(lambda x:(x[1] > 242 and x[1] < 1070 and x[0] > 180 and x[0] < 955) or (x[1] > 160 and x[1] < 938 and x[0] > 550 and x[0] < 1790), map(lambda x:[x[0], x[1] + 140], Utils.find_all('combat/question_mark', sim)))
                l1 = [x for x in l1 if (not self.filter_blacklist(x, blacklist))]

                self.mystery_nodes_list = l1
                sim -= 0.005
        
            if filter_coordinates:
                self.mystery_nodes_list = Utils.filter_similar_coords(self.mystery_nodes_list)
            
            return self.mystery_nodes_list

    def filter_blacklist(self, coord, blacklist):
        for y in blacklist:
            if abs(coord[0] - y[0]) < 40 and abs(coord[1] - y[1]) < 40:
                return True
        return False

    def get_fleet_location(self):
        """Method to get the fleet's current location. Note it uses the green
        fleet marker to find the location but returns around the area of the
        feet of the flagship

        Returns:
            array: An array containing the x and y coordinates of the fleet's
            current location.
        """
        coords = [0, 0]
        count = 0

        while coords == [0, 0]:
            Utils.update_screen()
            count += 1

            if count > 4:
                Utils.swipe(960, 540, 960, 540 + 150 + count * 20, 100)
                Utils.update_screen()

            if Utils.find('combat/fleet_ammo', 0.8):
                coords = Utils.find('combat/fleet_ammo', 0.8)
                coords = [coords.x + 140, coords.y + 225 - count * 20]
            elif Utils.find('combat/fleet_arrow', 0.9):
                coords = Utils.find('combat/fleet_arrow', 0.9)
                coords = [coords.x + 25, coords.y + 320 - count * 20]

            if count > 4:
                Utils.swipe(960, 540 + 150 + count * 20, 960, 540, 100)
            elif (math.isclose(coords[0], 160, abs_tol=30) & math.isclose(coords[1], 142, abs_tol=30)):
                coords = [0, 0]

            Utils.update_screen()
        return coords

    def get_closest_target(self, blacklist=[], location=[], mystery_node=False):
        """Method to get the enemy closest to the specified location. Note
        this will not always be the enemy that is actually closest due to the
        asset used to find enemies and when enemies are obstructed by terrain
        or the second fleet

        Args:
            blacklist(array, optional): Defaults to []. An array of
            coordinates to exclude when searching for the closest enemy

            location(array, optional): Defaults to []. An array of coordinates
            to replace the fleet location.

        Returns:
            array: An array containing the x and y coordinates of the closest
            enemy to the specified location
        """
        boss = True if location else False
        fleet_location = self.get_fleet_location()

        if location == []:
           location = fleet_location

        if mystery_node and self.chapter_map[0].isdigit():
            mystery_nodes = self.get_mystery_nodes(blacklist, boss)
            if self.config.combat['focus_on_mystery_nodes'] and len(mystery_nodes) > 0:
                # giving mystery nodes top priority and ignoring enemies
                targets = mystery_nodes
                Logger.log_info("Prioritizing mystery nodes.")
            else:
                # mystery nodes are valid targets, same as enemies
                enemies = self.get_enemies(blacklist, boss)
                targets = enemies + mystery_nodes
        else:
            # target only enemy mobs
            targets = self.get_enemies(blacklist, boss)
            
        closest = targets[Utils.find_closest(targets, location)[1]]

        Logger.log_info('Current location is: {}'.format(fleet_location))
        Logger.log_info('Targets found at: {}'.format(targets))
        Logger.log_info('Closest target is at {}'.format(closest))

        if closest in self.enemies_list:
            x = self.enemies_list.index(closest)
            del self.enemies_list[x]
            target_type = "enemy"
        else:
            x = self.mystery_nodes_list.index(closest)
            del self.mystery_nodes_list[x]
            target_type = "mystery_node"

        return [closest[0], closest[1], target_type]

    def check_movement_threads(self):
        thread_check_button_evade = Thread(
            target=self.check_movement_threads_func, args=("combat/button_evade",))
        thread_check_failed_evade = Thread(
            target=self.check_movement_threads_func, args=("combat/alert_failed_evade",))
        thread_check_alert_info = Thread(
            target=self.check_movement_threads_func, args=("menu/alert_info",))
        thread_check_item_found = Thread(
            target=self.check_movement_threads_func, args=("menu/item_found",))
        thread_check_menu_formation = Thread(
            target=self.check_movement_threads_func, args=("combat/menu_formation",))
        thread_check_menu_loading = Thread(
            target=self.check_movement_threads_func, args=("combat/menu_loading",))

        Utils.multithreader([
            thread_check_button_evade, thread_check_failed_evade,
            thread_check_alert_info, thread_check_item_found,
            thread_check_menu_formation, thread_check_menu_loading])

        return self.movement_event

    def check_movement_threads_func(self, event):
        self.movement_event[event] = (
            True
            if (Utils.find(event))
            else False)