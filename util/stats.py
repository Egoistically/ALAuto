# kcauto  Copyright (C) 2017  Minyoung Choi

from datetime import datetime
from util.logger import Logger


class Stats(object):
    def __init__(self, config):
        """Initializes the Stats module.

        Args:
            config (Config): azurlane-auto Config instance
        """
        self.reset_stats()
        self.config = config

    def reset_stats(self):
        """Resets all stats to 0
        """
        self.start_time = datetime.now()
        self.commissions_started = 0
        self.commissions_received = 0
        self.combat_attempted = 0
        self.combat_done = 0

    def _pretty_timedelta(self, delta):
        """Generate a human-readable time delta representation of how long the
        script has been running. Prettify code taken from:
        https://stackoverflow.com/q/538666

        Args:
            delta (timedelta): timedelta representation of current time minus
                the script start time

        Returns:
            str: human-readable representation of timedelta
        """

        pretty_string = "{} days ".format(delta.days) if delta.days else ""
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        pretty_string += "{} hours {} minutes".format(
            hours, minutes, seconds)
        return pretty_string

    def _pretty_perhour(self, count, hours):
        """Generate a sensible count and count-per-hour string representation,
        returning just the count if the hours count is below 1 or count is 0.

        Args:
            count (int): total count
            hours (float): total hours to calculate count-per-hour with

        Returns:
            str: count and human-readable representation of count-per-hour if
                hours < 1 or count is 0
        """
        if hours < 1 or count == 0:
            return count
        return "{} ({:0.2f}/hr)".format(count, count / hours)

    def print_stats(self, oil):
        """Prints a summary of all the stats to console.
        """
        delta = datetime.now() - self.start_time
        hours = delta.total_seconds() / 3600

        Logger.log_success("Current oil: " + str(oil))
        if self.config.commissions['enabled']:
            Logger.log_success(
                "Commissions sent: {} / received: {}".format(
                    self._pretty_perhour(self.commissions_started, hours),
                    self._pretty_perhour(self.commissions_received, hours)))

        if self.config.combat['enabled']:
            Logger.log_success("Combat done: {} / attempted: {}".format(
                self._pretty_perhour(self.combat_done, hours),
                self._pretty_perhour(self.combat_attempted, hours)))

        Logger.log_success(
            "ALAuto has been running for {} (started on {})".format(
                self._pretty_timedelta(delta),
                self.start_time.strftime('%Y-%m-%d %H:%M:%S')))

    def increment_commissions_started(self):
        """Increments the number of commissions started
        """
        self.commissions_started += 1

    def increment_commissions_received(self):
        """Increments the number of commissions received
        """
        self.commissions_received += 1

    def increment_combat_attempted(self):
        """Increments the number of sorties attempted
        """
        self.combat_attempted += 1

    def increment_combat_done(self):
        """Increments the number of sorties completed
        """
        self.combat_done += 1
