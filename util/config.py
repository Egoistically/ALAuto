import configparser
import sys
from copy import deepcopy
from util.logger import Logger


class Config(object):
    """Config module that reads and validates the config to be passed to
    azurlane-auto
    """

    def __init__(self, config_file):
        """Initializes the config file by changing the working directory to the
        root azurlane-auto folder and reading the passed in config file.

        Args:
            config_file (string): Name of config file.
        """
        Logger.log_msg("Initializing config module")
        self.config_file = config_file
        self.ok = False
        self.initialized = False
        self.scheduled_sleep = {}
        self.scheduled_stop = {}
        self.combat = {'enabled': False}
        self.commissions = {'enabled': False}
        self.enhancement = {'enabled': False}
        self.missions = {'enabled': False}
        self.retirement = {'enabled': False}
        self.network = {}
        self.read()

    def read(self):
        backup_config = deepcopy(self.__dict__)
        config = configparser.ConfigParser()
        config.read(self.config_file)
        self.network['service'] = config.get('Network', 'Service')
        if config.getboolean('Combat', 'Enabled'):
            self._read_combat(config)
        else:
            self.combat = {'enabled': False}
        self.commissions['enabled'] = config.getboolean('Commissions', 'Enabled')
        self.enhancement['enabled'] = config.getboolean('Enhancement', 'Enabled')
        self.missions['enabled'] = config.getboolean('Missions', 'Enabled')
        self.retirement['enabled'] = config.getboolean('Retirement', 'Enabled')
        self.validate()
        if (self.ok and not self.initialized):
            Logger.log_msg("Starting ALAuto!")
            self.initialized = True
            self.changed = True
        elif (not self.ok and not self.initialized):
            Logger.log_error("Invalid config. Please check your config file.")
            sys.exit(1)
        elif (not self.ok and self.initialized):
            Logger.log_warning("Config change detected, but with problems. Rolling back config.")
            self._rollback_config(backup_config)
        elif (self.ok and self.initialized):
            if backup_config != self.__dict__:
                Logger.log_warning("Config change detected. Hot-reloading.")
                self.changed = True

    def _read_combat(self, config):
        """Method to parse the Combat settings of the passed in config.
        Args:
            config (ConfigParser): ConfigParser instance
        """
        self.combat['enabled'] = True
        self.combat['map'] = config.get('Combat', 'Map')
        self.combat['retire_cycle'] = config.get('Combat', 'RetireCycle')

    def validate(self):
        def try_cast_to_int(val):
            """Helper function that attempts to coerce the val to an int,
            returning the val as-is the cast fails
            Args:
                val (string): string to attempt to cast to int
            Returns:
                int, str: int if the cast was successful; the original str
                    representation otherwise
            """
            try:
                return int(val)
            except ValueError:
                return val

        """Method to validate the passed in config file
        """
        if not self.initialized:
            Logger.log_msg("Validating config")
        self.ok = True

        if self.combat['enabled']:
            map = self.combat['map'].split('-')
            valid_chapters = list(range(1, 12)) + ['E']
            valid_levels = list(range(1, 12)) + ['A1', 'A2', 'A3', 'A4',
                                                 'B1', 'B2', 'B3', 'B4',
                                                 'C1', 'C2', 'C3', 'C4',
                                                 'D1', 'D2', 'D3', 'D4']
            if (try_cast_to_int(map[0]) not in valid_chapters or
               try_cast_to_int(map[1]) not in valid_levels):
                self.ok = False
                Logger.log_error("Invalid Map Selected: '{}'."
                                 .format(self.combat['map']))

    def _rollback_config(self, config):
        """Method to roll back the config to the passed in config's.
        Args:
            config (dict): previously backed up config
        """
        for key in config:
            setattr(self, key, config['key'])
