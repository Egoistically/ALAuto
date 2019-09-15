import math
from util.logger import Logger
from util.utils import Region, Utils
from modules.retirement import RetirementModule
from scipy import spatial

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
        self.exit = 0
        self.l = []
        self.blacklist = []
        self.chapter_map = self.config.combat['map']
        self.region = {
            'menu_button_battle': Region(1517, 442, 209, 206),
            'map_summary_go': Region(1289, 743, 280, 79),
            'fleet_menu_go': Region(1485, 872, 270, 74),
            'combat_ambush_evade': Region(1493, 682, 208, 56),
            'combat_com_confirm': Region(848, 740, 224, 56),
            'combat_end_confirm': Region(1520, 963, 216, 58),
            'menu_combat_start': Region(1578, 921, 270, 70),
            'menu_nav_back': Region(54, 57, 67, 67)
        }

    def combat_logic_wrapper(self):
        """Method that fires off the necessary child methods that encapsulates
        the entire action of sortieing combat fleets and resolving combat.

        Returns:
            bool: True if the combat cycle was complete
        """
        finished = False
        self.exit = 0
        self.l.clear()
        self.blacklist.clear()

        while finished == False:
            Utils.update_screen()

            if Utils.find("menu_sort_button"):
                #Logger.log_error("I should kill myself.")
                exit
            if Utils.find("commission_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("menu_battle"):
                #Logger.log_msg("Found menu battle button.")
                Utils.touch_randomly(self.region["menu_button_battle"])
                Utils.script_sleep(0.5)
                continue
            if Utils.find_and_touch('map_{}'.format(self.chapter_map), 0.99):
                Logger.log_msg("Found specified map.")
                continue
            if Utils.find("map_select_fleet"):
                #Logger.log_msg("Found fleet select go button.")
                Utils.touch_randomly(self.region["fleet_menu_go"])
                continue
            if Utils.find("map_summary_go"):
                #Logger.log_msg("Found map summary go button.")
                Utils.touch_randomly(self.region["map_summary_go"])
                continue
            if Utils.find("combat_retreat"):
                #Logger.log_msg("Found retreat button, starting clear function.")
                self.clear_map()
            if self.exit == 1:
                Logger.log_msg("Boss successfully defeated, going back to menu.")
                self.stats.increment_combat_done()
                finished = True
                continue
            if self.exit == 2:
                Logger.log_error("Mood too low, retreating and sleeping.")
                finished = True
                continue

        Utils.script_sleep(1)
        Utils.touch_randomly(self.region["menu_nav_back"])

        Utils.update_screen()
        if not Utils.find("menu_battle"):
            Utils.touch_randomly(self.region["menu_nav_back"])

        return self.exit

    def battle_handler(self):
        Logger.log_msg("Starting battle.")
        Utils.touch_randomly(self.region["menu_combat_start"])
        Utils.script_sleep(4)

        while True:
            Utils.update_screen()
            
            if Utils.find("menu_mood_low"):
                self.retreat_handler()
                return
            if Utils.find("menu_sort_button"):
                self.run_retirement()
                continue
            if Utils.find("commission_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("combat_pause", 0.7):
                #Logger.log_msg("In battle.")
                Utils.script_sleep(5)
                continue
            if Utils.find("combat_touch_to_continue"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                continue
            if Utils.find("item_found"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                Utils.script_sleep(1)
                continue
            if Utils.find("drop_ssr"):
                Logger.log_msg("Received SSR ship as drop.")
                Utils.touch_randomly(Region(1228, 103, 692, 735))
                continue
            if Utils.find("drop_elite"):
                Logger.log_msg("Received ELITE ship as drop.")
                Utils.touch_randomly(Region(1228, 103, 692, 735))
                continue
            if Utils.find("combat_confirm"):
                Logger.log_msg("Combat ended.")
                Utils.touch_randomly(self.region["combat_end_confirm"])
                Utils.script_sleep(1)
                return

    def movement_handler(self, location):
        Logger.log_msg("Moving towards objective.")
        count = 0

        while True:
            Utils.update_screen()

            if Utils.find("combat_ambush_evade"):
                Logger.log_msg("Ambush was found, trying to evade.")
                Utils.touch_randomly(self.region["combat_ambush_evade"])
                continue
            if Utils.find("combat_ambush_failed"):
                Logger.log_warning("Failed to evade ambush.")
                Utils.touch_randomly(self.region["menu_combat_start"])
                self.battle_handler()
                continue
            if Utils.find("item_found"):
                Logger.log_msg("Item found on node.")
                Utils.touch_randomly(Region(661, 840, 598, 203))
                continue
            if Utils.find("menu_formation"):
                return
            else:
                if count % 3 == 0:
                    Utils.touch(location)
                count += 1

    def unable_handler(self, coords):
        Logger.log_msg("Unable to reach boss.")
        enemy_coords = self.get_enemies(self.blacklist)
        closest_to_boss = enemy_coords[Utils.find_closest(enemy_coords, coords)[1]]

        Utils.touch(closest_to_boss)
        Utils.script_sleep(1)
        Utils.update_screen()

        if Utils.find("combat_unable_reach"):
            Logger.log_warning("Unable to reach next to boss.")
            self.blacklist.append(closest_to_boss)
            closest_enemy = self.get_closest_enemy(self.blacklist)

            self.movement_handler(closest_enemy)
            self.battle_handler()
            return
        else:
            self.movement_handler(closest_to_boss)
            self.battle_handler()
            return

    def retreat_handler(self):
        Logger.log_msg("Retreating...")
        
        while True:
            Utils.update_screen()

            if Utils.find("menu_mood_low"):
                Utils.touch_randomly(Region(613, 731, 241, 69))
                continue
            if Utils.find("menu_formation"):
                Utils.touch_randomly(self.region["menu_nav_back"])
                continue
            if Utils.find("combat_retreat"):
                Utils.touch_randomly(Region(1130, 985, 243, 60))
                continue
            if Utils.find("combat_com_confirm"):
                Utils.touch_randomly(Region(1065, 732, 235, 68))
                continue
            if Utils.find("map_hard_mode"):
                self.exit = 2
                return

    def clear_map(self):
        #Logger.log_msg("Started clear map function.")
        Utils.script_sleep(2.5)
        enemy_coords = self.get_closest_enemy(self.blacklist)

        while True:
            Utils.update_screen()

            if self.exit == 1 or self.exit == 2:
                return
            if Utils.find("commission_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("enemy_fleet_boss", 0.9):
                Logger.log_msg("Boss fleet was found.")
                boss_coords = Utils.find("enemy_fleet_boss", 0.9)
                self.clear_boss(boss_coords)
                continue
            if enemy_coords == None:
                enemy_coords = self.get_closest_enemy(self.blacklist)
                continue
            if enemy_coords:
                Logger.log_msg("Navigating to enemy.")
                Utils.touch(enemy_coords)
                Utils.update_screen()
            if Utils.find("combat_unable_reach", 0.8):
                Logger.log_warning("Unable to reach the target.")
                self.blacklist.append(enemy_coords)
                enemy_coords = None
                continue
            else:
                self.movement_handler(enemy_coords)
                enemy_coords = None
                self.battle_handler()

                Utils.script_sleep(3)
                self.blacklist.clear()
                continue

    def clear_boss(self, coords):
        #Logger.log_msg("Started boss function.")
        boss_coords = [coords.x + 50, coords.y + 25]

        self.l.clear()
        self.blacklist.clear()
        Utils.touch(boss_coords)

        while True:
            Utils.update_screen()

            if Utils.find("combat_unable_reach", 0.8):
                Logger.log_msg("Unable to reach boss.")
                self.unable_handler(boss_coords)
                continue
            if Utils.find("commission_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            else:
                self.movement_handler(boss_coords)
                self.battle_handler()
                self.exit = 1
                return

    def get_enemies(self, blacklist=[]):
        sim = 0.99
        if blacklist != []:
            Logger.log_msg('Blacklist: ' + str(blacklist))

        while self.l == []:
            Utils.update_screen()

            l1 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] - 3, x[1] - 45],Utils.find_all('enemy_fleet_level', sim - 0.15)))
            l1 = [x for x in l1 if (x not in blacklist)]
            l2 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy_fleet_1_down', sim)))
            l2 = [x for x in l2 if (x not in blacklist)]
            l3 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy_fleet_2_down', sim)))
            l3 = [x for x in l3 if (x not in blacklist)]
            l4 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 130],Utils.find_all('enemy_fleet_3_up', sim - 0.06)))
            l4 = [x for x in l4 if (x not in blacklist)]
            l5 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy_fleet_3_down', sim - 0.06)))
            l5 = [x for x in l5 if (x not in blacklist)]

            self.l = l1 + l2 + l3 + l4 + l5
            sim -= 0.005
            #print(str(l1) + ' ' + str(l2) + ' ' + str(l3) + ' ' + str(l4) + ' ' + str(l5))
            #print(str(self.l) + ' ' + str(sim))
        
        self.l = Utils.filter_similar_coords(self.l)
        return self.l

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
            
            if Utils.find('combat_fleet_ammo', 0.8):
                coords = Utils.find('combat_fleet_ammo', 0.8)
                coords = [coords.x + 140, coords.y + 225 - count * 20]
            elif Utils.find('combat_fleet_arrow', 0.9):
                coords = Utils.find('combat_fleet_arrow', 0.9)
                coords = [coords.x + 25, coords.y + 320 - count * 20]

            if count > 4:
                Utils.swipe(960, 540 + 150 + count * 20, 960, 540, 100)
            elif (math.isclose(coords[0], 160, abs_tol=30) & math.isclose(coords[1], 142, abs_tol=30)):
                coords = [0, 0]

            Utils.update_screen()
        return coords

        # else: 
        #     coords = Utils.scroll_find('combat_fleet_marker', 250, 175, 0.95)
        #     # swipe back so enemies don't end up out of screen, only Y value
        #     Utils.swipe(640, 360 + 175, 640, 360 - 175, 300)
        #     return [coords.x, coords.y - 30]

    def get_closest_enemy(self, blacklist=[]):
        """Method to get the enemy closest to the fleet's current location. Note
        this will not always be the enemy that is actually closest due to the
        asset used to find enemies and when enemies are obstructed by terrain
        or the second fleet

        Args:
            blacklist(array, optional): Defaults to []. An array of
            coordinates to exclude when searching for the closest enemy

        Returns:
            array: An array containing the x and y coordinates of the closest
            enemy to the fleet's current location
        """
        while True: 
            fleet_location = self.get_fleet_location()
            enemies = self.get_enemies(self.blacklist)
            closest = enemies[Utils.find_closest(enemies, fleet_location)[1]]

            Logger.log_msg('Current location is: {}'.format(fleet_location))
            Logger.log_msg('Enemies found at: {}'.format(enemies))
            Logger.log_msg('Closest enemy is at {}'.format(closest))

            if closest in self.l:
                x = self.l.index(closest)
                del self.l[x]

            return [closest[0], closest[1]]