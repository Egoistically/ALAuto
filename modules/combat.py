import math
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
        self.exit = 0
        self.l = []
        self.blacklist = []
        self.movement_event = {}
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
            int: 1 if boss was defeated, 2 if morale is too low and 3 if dock is full.
        """
        self.exit = 0
        self.l.clear()
        self.blacklist.clear()

        while True:
            Utils.update_screen()

            if Utils.find("menu/button_sort"):
                Utils.touch_randomly(Region(1312, 263, 64, 56))
                self.exit = 3
            if Utils.find("commission/button_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("menu/button_battle"):
                Logger.log_debug("Found menu battle button.")
                Utils.touch_randomly(self.region["menu_button_battle"])
                Utils.script_sleep(0.5)
                continue
            if Utils.find_and_touch('maps/map_{}'.format(self.chapter_map), 0.99):
                Logger.log_msg("Found specified map.")
                continue
            if Utils.find("combat/menu_select_fleet"):
                Logger.log_debug("Found fleet select go button.")
                Utils.touch_randomly(self.region["fleet_menu_go"])
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
            if self.exit == 1:
                Logger.log_msg("Boss successfully defeated, going back to menu.")
                self.stats.increment_combat_done()
                break
            if self.exit == 2:
                Logger.log_warning("Ships morale is too low, entering standby mode for an hour.")
                self.stats.increment_combat_attempted()
                break
            if self.exit == 3:
                Logger.log_warning("Dock is full, need to retire.")
                self.stats.increment_combat_attempted()
                break

        Utils.script_sleep(1)

        while not Utils.find("menu/button_battle"):
            Utils.touch_randomly(Region(54, 57, 67, 67))
            Utils.script_sleep(1)
            Utils.update_screen()

        return self.exit

    def battle_handler(self, boss=False):
        Logger.log_msg("Starting combat.")

        while not Utils.find("combat/menu_loading", 0.8):
            Utils.update_screen()

            if Utils.find("combat/alert_morale_low") or Utils.find("menu/button_sort"):
                self.retreat_handler()
                return
            else:
                Utils.touch_randomly(self.region["menu_combat_start"])
                Utils.script_sleep(1)
        
        Utils.script_sleep(4)

        while True:
            Utils.update_screen()
            
            if Utils.find("combat/alert_lock"):
                Logger.log_msg("Locking received ship.")
                Utils.touch_randomly(Region(1086, 739, 200, 55))
                continue
            if Utils.find("combat/combat_pause", 0.7):
                Logger.log_debug("In battle.")
                Utils.script_sleep(5)
                continue
            if Utils.find("combat/menu_touch2continue"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                continue
            if Utils.find("menu/item_found"):
                Utils.touch_randomly(Region(661, 840, 598, 203))
                Utils.script_sleep(1)
                continue
            if Utils.find("menu/drop_ssr"):
                Logger.log_msg("Received SSR ship as drop.")
                Utils.touch_randomly(Region(1228, 103, 692, 735))
                continue
            if Utils.find("menu/drop_elite"):
                Logger.log_msg("Received ELITE ship as drop.")
                Utils.touch_randomly(Region(1228, 103, 692, 735))
                continue
            if Utils.find("combat/button_confirm"):
                Logger.log_msg("Combat ended.")
                Utils.touch_randomly(self.region["combat_end_confirm"])
                Utils.script_sleep(1)
                if boss:
                    return
                Utils.update_screen()
            if Utils.find("commission/button_confirm"):
                Logger.log_msg("Found commission info message.")
                Utils.touch_randomly(self.region["combat_com_confirm"])
                continue
            if Utils.find("combat/button_retreat"):
                Utils.script_sleep(3)
                Utils.touch_randomly(Region(1617, 593, 4, 146))
                return

    def movement_handler(self, target_location):
        """
        Method that handles the fleet movement until it reach its target (mystery node or enemy node).
        If the coordinates are wrong, they will be blacklisted and another set of coordinates to work on is obtained.
        If the target is a mystery node and what is found is ammo, then the method will fall in the blacklist case
        and search for another enemy: this is inefficient and should be improved, but it works.

        Returns:
            (int): 1 if a fight is needed, otherwise 0.
        """
        Logger.log_msg("Moving towards objective.")
        count = 0
        location = [target_location[0], target_location[1]]

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
                Utils.touch_randomly(self.region["menu_combat_start"])
                self.battle_handler()
                continue
            if event["menu/item_found"]:
                Logger.log_msg("Item found on node.")
                Utils.touch_randomly(Region(661, 840, 598, 203))
                if target_location[2] == "question_mark":
                    Logger.log_msg("Target reached.")
                    return 0
                continue
            if event["menu/alert_info"]:
                Logger.log_debug("Found alert.")
                Utils.find_and_touch("menu/alert_close")
                continue

            if event["combat/menu_formation"] or event["combat/menu_loading"]:
                return 1

            else:
                if count % 3 == 0:
                    Utils.touch(location)
                if count > 21:
                    Logger.log_msg("Blacklisting location and searching for another enemy.")
                    self.blacklist.append(location)
                    self.l.clear()

                    location = self.get_closest_enemy(self.blacklist)
                    count = 0
                count += 1

    def unable_handler(self, coords):
        Logger.log_msg("Unable to reach boss function started.")
        closest_to_boss = self.get_closest_enemy(self.blacklist, coords)

        Utils.touch(closest_to_boss)
        Utils.script_sleep(1)
        Utils.update_screen()

        if Utils.find("combat/alert_unable_reach"):
            Logger.log_warning("Unable to reach next to boss.")
            self.blacklist.append(closest_to_boss)

            while True:
                closest_enemy = self.get_closest_enemy(self.blacklist)
                Utils.touch(closest_enemy)
                Utils.update_screen()

                if Utils.find("combat/alert_unable_reach"):
                    self.blacklist.append(closest_to_boss)
                else:
                    break
                
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

            if Utils.find("combat/alert_morale_low"):
                Utils.touch_randomly(Region(613, 731, 241, 69))
                self.exit = 2
                continue
            if Utils.find("menu/button_sort"):
                Utils.touch_randomly(Region(1312, 263, 64, 56))
                self.exit = 3
                continue
            if Utils.find("combat/menu_formation"):
                Utils.touch_randomly(self.region["menu_nav_back"])
                continue
            if Utils.find("combat/button_retreat"):
                Utils.touch_randomly(Region(1130, 985, 243, 60))
                continue
            if Utils.find("commission/button_confirm"):
                Utils.touch_randomly(Region(1065, 732, 235, 68))
                continue
            if Utils.find("menu/button_hard_mode"):
                return

    def clear_map(self):
        Logger.log_msg("Started map clear.")
        Utils.script_sleep(2.5)

        #hide strat menu
        Utils.touch_randomly(Region(1617, 593, 4, 146))
        #swipe map to the left
        Utils.swipe(960, 540, 1300, 540, 100)

        enemy_coords = self.get_closest_enemy(self.blacklist)
        target_coords = [enemy_coords[0], enemy_coords[1], "enemy"]

        while True:
            Utils.update_screen()

            if Utils.find("combat/alert_unable_battle"):
                Logger.log_warning("Failed to defeat enemy.")
                Utils.touch_randomly(Region(869, 741, 185, 48))
                return False
            if self.exit is not 0:
                return True
            if Utils.find("enemy/fleet_boss", 0.9):
                Logger.log_msg("Boss fleet was found.")
                boss_coords = Utils.find("enemy/fleet_boss", 0.9)
                self.clear_boss(boss_coords)
                continue
            if target_coords == None:
                if Utils.find("combat/question_mark", 0.9):
                    target_coords = self.get_closest_target(self.blacklist)
                    #if it is a an item (question_mark), tap a bit lower
                    if target_coords[2] == "question_mark":
                        #coord y
                        target_coords[1] += 175
                else:
                    closest_enemy = self.get_closest_enemy(self.blacklist)
                    target_coords = [closest_enemy[0], closest_enemy[1], "enemy"]
                continue
            if target_coords:
                enemy_coords = [target_coords[0], target_coords[1]]
                Utils.touch(enemy_coords)
                Utils.update_screen()
            if Utils.find("combat/alert_unable_reach", 0.8):
                Logger.log_warning("Unable to reach the target.")
                self.blacklist.append(enemy_coords)
                target_coords = None
                enemy_coords = None
                continue
            else:
                movement_result = self.movement_handler(target_coords)
                if movement_result == 1:
                    self.battle_handler()
                target_coords = None
                enemy_coords = None

                self.blacklist.clear()
                continue

    def clear_boss(self, coords):
        Logger.log_debug("Started boss function.")
        boss_coords = [coords.x + 50, coords.y + 25]

        self.l.clear()
        self.blacklist.clear()

        while True:
            Utils.touch(boss_coords)
            Utils.update_screen()

            if Utils.find("combat/alert_unable_reach", 0.8):
                Logger.log_msg("Unable to reach boss.")
                self.unable_handler(boss_coords)
                continue
            else:
                boss_coords.append("boss")
                self.movement_handler(boss_coords)
                self.battle_handler(boss=True)
                self.exit = 1
                return

    def get_enemies(self, blacklist=[]):
        sim = 0.99
        if blacklist != []:
            Logger.log_info('Blacklist: ' + str(blacklist))
            self.l = [x for x in self.l if (x not in blacklist)]

        while self.l == []:
            Utils.update_screen()

            l1 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] - 3, x[1] - 45],Utils.find_all('enemy/fleet_level', sim - 0.15)))
            l1 = [x for x in l1 if (x not in blacklist)]
            l2 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy/fleet_1_down', sim)))
            l2 = [x for x in l2 if (x not in blacklist)]
            l3 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy/fleet_2_down', sim - 0.02)))
            l3 = [x for x in l3 if (x not in blacklist)]
            l4 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 130],Utils.find_all('enemy/fleet_3_up', sim - 0.06)))
            l4 = [x for x in l4 if (x not in blacklist)]
            l5 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] + 75, x[1] + 110],Utils.find_all('enemy/fleet_3_down', sim - 0.06)))
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

    def get_closest_enemy(self, blacklist=[], location=[]):
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
        while True: 
            fleet_location = self.get_fleet_location()
            if location == []:
                location = fleet_location
            enemies = self.get_enemies(blacklist)
            closest = enemies[Utils.find_closest(enemies, location)[1]]

            Logger.log_info('Current location is: {}'.format(fleet_location))
            Logger.log_info('Enemies found at: {}'.format(enemies))
            Logger.log_info('Closest enemy is at {}'.format(closest))

            if closest in self.l:
                x = self.l.index(closest)
                del self.l[x]

            return [closest[0], closest[1]]

    def get_closest_target(self, blacklist=[], location=[]):
        """Method to get the closest target (enemy or item) to the specified location. Note
        this will not always be the target that is actually closest.

        Args:
            blacklist(array, optional): Defaults to []. An array of
            coordinates to exclude when searching for the closest enemy

            location(array, optional): Defaults to []. An array of coordinates
            to replace the fleet location.

        Returns:
            array: An array containing the x and y coordinates and the type of the closest
            target
        """
        while True: 
            fleet_location = self.get_fleet_location()
            if location == []:
                location = fleet_location
            #get all the enemies
            enemies = self.get_enemies(blacklist)
            #get all the question marks on the map
            sim = 0.99
            question_marks = []

            while question_marks == []:
                Utils.update_screen()

                l1 = filter(lambda x:x[1] > 80 and x[1] < 977 and x[0] > 180, map(lambda x:[x[0] - 3, x[1] - 45],Utils.find_all('combat/question_mark', sim - 0.09)))
                l1 = [x for x in l1 if (x not in blacklist)]

                question_marks = l1
                sim -= 0.005
                #print
        
            question_marks = Utils.filter_similar_coords(question_marks)
            #working on all possible targets
            targets = enemies + question_marks
            closest = targets[Utils.find_closest(targets, location)[1]]

            Logger.log_info('Current location is: {}'.format(fleet_location))
            Logger.log_info('Targets found at: {}'.format(enemies))
            Logger.log_info('Closest target is at {}'.format(closest))

            if closest in self.l:
                x = self.l.index(closest)
                del self.l[x]

            if closest in question_marks:
                return [closest[0], closest[1], "question_mark"]
            else:
                return [closest[0], closest[1], "enemy"]

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