import subprocess
from util.logger import Logger

class Adb(object):

    legacy = False
    service = ''
    transID = ''
    tcp = False

    def init(self):
        """Kills and starts a new ADB server
        """
        self.kill_server()
        return self.start_server() 


    def enable_legacy(self):
        """Method to enable legacy adb usage.
        """
        self.legacy = True
        return

    def start_server(self):
        """
        Starts the ADB server and makes sure the android device (emulator) is attached.

        Returns:
            (boolean): True if everything is ready, False otherwise.
        """
        cmd = ['adb', 'start-server']
        subprocess.call(cmd)
        """ hooking onto here, previous implementation of get-state
         is pointless since the script kills the ADB server in advance,
         now seperately connect via usb or tcp, tcp variable is set by main script"""
        if self.tcp:
            return self.connect_tcp()
        else:
            return self.connect_usb()

    def connect_tcp(self):
        cmd = ['adb', 'connect', self.service]
        response = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8')
        if (response.find('connected') == 0) or (response.find('already') == 0):
            self.assign_serial()
            if (self.transID is not None) and self.transID:
                return True
            Logger.log_error('Failure to assign transport_id.')  
            Logger.log_error('Please try updating your ADB installation. Current ADB version:')
            self.print_adb_version()
        return False

    def connect_usb(self):
        self.assign_serial()
        if (self.transID is not None) and self.transID:
            cmd = ['adb', '-t', self.transID, 'wait-for-device']
            Logger.log_msg('Waiting for device [' + self.service + '] to be authorized...')
            subprocess.call(cmd)
            Logger.log_msg('Device [' + self.service + '] authorized and connected.')
            return True
        Logger.log_error('Failure to assign transport_id. Is your device connected? Or is "transport_id" not supported in current ADB version? ')
        Logger.log_error('Try updating ADB if "transport_id:" does not exist in the info of your device when running "adb devices -l" in cmd.')
        Logger.log_error('Current ADB version:')
        self.print_adb_version()
        return False


    @staticmethod
    def kill_server():
        """Kills the ADB server
        """
        cmd = ['adb', 'kill-server']
        subprocess.call(cmd)

    @staticmethod
    def exec_out(args):
        """Executes the command via exec-out

        Args:
            args (string): Command to execute.

        Returns:
            tuple: A tuple containing stdoutdata and stderrdata
        """
        cmd = ['adb', '-t', Adb.transID , 'exec-out'] + args.split(' ')
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE)
        return process.communicate()[0]

    @staticmethod
    def shell(args):
        """Executes the command via adb shell

        Args:
            args (string): Command to execute.
        """
        cmd = ['adb', '-t', Adb.transID ,'shell'] + args.split(' ')
        Logger.log_debug(str(cmd))
        subprocess.call(cmd)

    @staticmethod
    def cmd(args):
        """Executes a general command of ADB

        Args:
            args (string): Command to execute.
        """
        cmd = ['adb', '-t', Adb.transID] + args.split(' ')
        Logger.log_debug(str(cmd))
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE)
        return process.communicate()[0]

    @classmethod
    def assign_serial(cls):
        cmd = ['adb', 'devices', '-l']
        response = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').splitlines()
        cls.sanitize_device_info(response)
        if not response:
            Logger.log_error('adb devices -l yielded no lines with "transport_id:"')
        cls.transID = cls.get_serial_trans(cls.service, response)

    @staticmethod
    def sanitize_device_info(string_list):
        for index in range(len(string_list) - 1, -1, -1):
            if 'transport_id:' not in string_list[index]:
                string_list.pop(index)

    @staticmethod
    def get_serial_trans(device, string_list):
        for index in range(len(string_list)):
            if device in string_list[index]:
                return string_list[index][string_list[index].index('transport_id:') + 13:]

    @staticmethod
    def print_adb_version():
        cmd = ['adb', '--version']
        response = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode('utf-8').splitlines()
        for version in response:
            Logger.log_error(version)
