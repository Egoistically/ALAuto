from util.logger import Logger
from util.config import Config
from util.utils import Utils, Region


class ResearchModule(object):
    def __init__(self, config, stats):
        """Initializes the Research module.

        Args:
            config (Config): ALAuto Config instance
        """
        self.enabled = True
        self.config = config
        self.stats = stats
        self.region = {
            'lab_tab': Region(1004, 1013, 162, 39),
            'exit_button': Region(51, 52, 71, 60),
            'research_academy': Region(825, 415, 260, 265),
            'project_click': Region(865, 155, 180, 100),
            'right_arrow': Region(1855, 525, 30, 30),
            'commence_tab': Region(650, 855, 215, 35),
            'main_menu_button': Region(1821, 28, 44, 42),
            'confirm_tab': Region(1095, 760, 190, 50)
        }

    def research_logic_wrapper(self):
        Logger.log_msg("Found lab alert.")
        Utils.touch_randomly(self.region["lab_tab"])

        while True:
            Utils.wait_update_screen(1)

            if self.config.research['enabled'] and Utils.find("research/research_academy_alert", 0.99):
                Logger.log_msg("Found research academy alert.")
                Utils.touch_randomly(self.region['research_academy'])
                Utils.script_sleep(1)
                Logger.log_msg("Searching for completed research.")

                if not self.collecting_research():
                    Logger.log_msg("Did not found any completed research.")

                started = False
                Logger.log_msg("Searching for project that matches config.")
                for research_loop in range(0,5):
                    if not self.research_cycle():
                        Utils.touch_randomly(self.region['right_arrow'])
                    else:
                        if self.start_project() == True:
                            Logger.log_success("Project started.")
                            started = True
                            break
                        else:
                            Logger.log_warning("Unable to start project. Finding a new one.")
                            Utils.touch_randomly(self.region['right_arrow'])

                if started == False:
                    Logger.log_error("Unable to find project that matches current configuration.")
                            
             
                Logger.log_msg("Going back to main menu.")       
            else:
                Logger.log_msg("Shipyard or Fleet Tech alert detected, ignoring it.")
            Utils.touch_randomly(self.region['main_menu_button'])
            Utils.wait_update_screen(1)
            return True
                
    def research_cycle(self):
            Utils.wait_update_screen(1)
            if not self.config.research['8Hours'] and Utils.find("research/8h", 0.99):
                return False
            if not self.config.research['6Hours'] and Utils.find("research/6h", 0.99):
                return False
            if not self.config.research['5Hours'] and Utils.find("research/5h", 0.99):
                return False
            if not self.config.research['4Hours'] and Utils.find("research/4h", 0.99):
                return False
            if not self.config.research['2Hours30Minutes'] and Utils.find("research/2_30h", 0.99):
                return False
            if not self.config.research['2Hours'] and Utils.find("research/2h", 0.99):
                return False
            if not self.config.research['1Hour30Minutes'] and Utils.find("research/1_30h", 0.99):
                return False
            if not self.config.research['1Hour'] and Utils.find("research/1h", 0.99):
                return False
            if not self.config.research['30Minutes'] and Utils.find("research/30m", 0.99):
                return False
            if self.config.research['WithoutRequirements'] and not Utils.find("research/nothing", 0.99):
                return False
            if not self.config.research['AllowConsumingCoins'] and Utils.find("research/coins", 0.99):
                return False
            if not self.config.research['AllowConsumingCubes'] and Utils.find("research/cubes", 0.99):
                return False
            if self.config.research['AwardMustContainPRBlueprint'] and not Utils.find("research/PRBlueprint"):
                return False
            if not self.config.research['AllowFreeProjects'] and Utils.find("research/free", 0.99):
                return False
            if not self.config.research['12Hours'] and Utils.find("research/12h", 0.99):
                return False
            else:
                 return True

    def start_project(self):
        Utils.touch_randomly(self.region['commence_tab'])
        Utils.wait_update_screen(1)
        #solution for projects that don't require confirmation.
        if Utils.find("research/terminate", 0.99):
            return True

        if Utils.find("research/confirm", 0.99):
                Utils.touch_randomly(self.region['confirm_tab'])
                Utils.wait_update_screen(1)
                if Utils.find("research/terminate", 0.99):
                    return True

                else:
                    return False

    def collecting_research(self):
        Utils.touch_randomly(self.region['project_click'])
        Utils.wait_update_screen(1)
        if Utils.find("research/item_found"):
            Logger.log_msg("Found completed research project.")
            Utils.touch_randomly(self.region['project_click'])
            Utils.script_sleep(1)
            Utils.touch_randomly(self.region['project_click'])
            return True
        else:
            #solution for azur lane bug
            for searching in range(0,5):
                Utils.touch_randomly(self.region['right_arrow'])
                Utils.wait_update_screen(1)
                if Utils.find("research/item_found"):
                    Logger.log_msg("Found completed research project.")
                    Utils.script_sleep(1.5)
                    Utils.touch_randomly(self.region['project_click'])
                    Utils.script_sleep(1)
                    Utils.touch_randomly(self.region['project_click'])
                    return True
