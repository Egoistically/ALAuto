import subprocess
from util.logger import Logger

class Adb(object):

    legacy = False
    service = ''
    device = ''

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
        #checking the emulator state
        cmd = ['adb', self.device, 'get-state']
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell=True)
        #processing only the std_out data, if there is an error it will be sent to std_err,
        #so if the get-state fails ('error: no emulators found') => state=''
        state = process.communicate()[0].decode()
        if state.find('device') == -1:
            #the emulator is not attached, trying to connect using service info
            cmd = ['adb', 'connect', self.service]
            process = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell=True)
            std_out = process.communicate()[0].decode()
            return std_out.find('connected') == 0
        else:
            return True

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
        cmd = ['adb', Adb.device, 'exec-out'] + args.split(' ')
        process = subprocess.Popen(cmd, stdout = subprocess.PIPE, shell = True)
        return process.communicate()[0]

    @staticmethod
    def shell(args):
        """Executes the command via adb shell

        Args:
            args (string): Command to execute.
        """
        cmd = ['adb', Adb.device, 'shell'] + args.split(' ')
        Logger.log_debug(str(cmd))
        subprocess.call(cmd, shell=True)
