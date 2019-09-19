import subprocess
from util.logger import Logger

class Adb(object):

    service = ''

    def init(self):
        """Kills and starts a new ADB server
        """
        self.kill_server()
        return self.start_server()

    def start_server(self):
        """Starts the ADB server
        """
        cmd = ['adb', 'start-server']
        subprocess.call(cmd)
        cmd = ['adb', 'connect', self.service]
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell=True)
        str = process.communicate()[0].decode()
        return str.find('unable') == -1

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
        cmd = ['adb', 'exec-out'] + args.split(' ')
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
        return process.communicate()[0]

    @staticmethod
    def shell(args):
        """Executes the command via adb shell

        Args:
            args (string): Command to execute.
        """
        cmd = ['adb', 'shell'] + args.split(' ')
        Logger.log_debug(str(cmd))
        subprocess.call(cmd, shell=True)
