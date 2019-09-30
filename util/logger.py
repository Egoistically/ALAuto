# kcauto  Copyright (C) 2017  Minyoung Choi

from time import strftime
import platform
import subprocess


class Logger(object):

    debug = False

    if platform.system().lower() == 'windows':
        subprocess.call('', shell=True)

    CLR_MSG = '\033[94m'
    CLR_SUCCESS = '\033[92m'
    CLR_WARNING = '\033[93m'
    CLR_ERROR = '\033[91m'
    CLR_INFO = '\u001b[35m'
    CLR_END = '\033[0m'

    def enable_debugging(self):
        """Method to enable debugging logs.
        """
        self.debug = True
        return

    @staticmethod
    def log_format(msg):
        """Method to add a timestamp to a log message

        Args:
            msg (string): log msg

        Returns:
            str: log msg with timestamp appended
        """
        return "[{}] {}".format(strftime("%Y-%m-%d %H:%M:%S"), msg)

    @classmethod
    def log_msg(cls, msg):
        """Method to print a log message to the console, with the 'msg' colors

        Args:
            msg (string): log msg
        """
        print("{0}{1}{2}".format(
            cls.CLR_MSG, cls.log_format(msg), cls.CLR_END))

    @classmethod
    def log_success(cls, msg):
        """Method to print a log message to the console, with the 'success'
        colors

        Args:
            msg (string): log msg
        """
        print("{}{}{}".format(
            cls.CLR_SUCCESS, cls.log_format(msg), cls.CLR_END))

    @classmethod
    def log_warning(cls, msg):
        """Method to print a log message to the console, with the 'warning'
        colors

        Args:
            msg (string): log msg
        """
        print("{}{}{}".format(
            cls.CLR_WARNING, cls.log_format(msg), cls.CLR_END))

    @classmethod
    def log_error(cls, msg):
        """Method to print a log message to the console, with the 'error'
        colors

        Args:
            msg (string): log msg
        """
        print("{}{}{}".format(
            cls.CLR_ERROR, cls.log_format(msg), cls.CLR_END))

    @classmethod
    def log_info(cls, msg):
        """Method to print a log message to the console, with the 'info'
        colors

        Args:
            msg (string): log msg
        """
        print("{}{}{}".format(
        cls.CLR_INFO, cls.log_format(msg), cls.CLR_END))

    @classmethod
    def log_debug(cls, msg):
        """Method to print a debug message to the console, with the 'msg'
        colors

        Args:
            msg (string): log msg
        """
        if not cls.debug: return
        print("{}".format(
        cls.log_format(msg)))