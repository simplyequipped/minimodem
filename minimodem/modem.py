'''A full duplex FSK soft modem utilizing the Unix application minimodem

The minimodem application can be installed on Debian systems with the command:
    sudo apt install minimodem

Classes:

    HDLC
    MiniModem
    Modem

Functions:

    get_alsa_device(device_desc[, device_mode=RX]) -> str

Constants:

    RX
    TX
'''


import os, subprocess, threading, time
from subprocess import PIPE, DEVNULL, TimeoutExpired, CalledProcessError


# Package constants
RX = 'rx'
TX = 'tx'

class HDLC:
    '''Defines packet framing flags similar to HDLC or PPP.
    
    Multiple characters per flag makes it less likely that receiver noise will emulate a flag.
    
    Constants:

        START
        STOP
    '''

    START = b'|->'
    STOP = b'<-|'

class MiniModem:
    '''Create and interact with a minimodem subprocess

    See the minimodem manpage for more information about the application.

    Attributes:
    
        mode : str, operating mode of the minimodem application (see module constants)
        alsa_dev : str | None, ALSA device formated as 'card,device' (ex. '2,0'), or None to use system default
        baudrate : int, baud rate of the modem
        process : object, subprocess.Popen instance of the minimodem application
        online: bool, status of the modem
        shellcmd: str, command string passed to subprocess.Popen

    Methods:

        __init__(self, mode, alsa_dev[, baudrate=300, start=True])
        start(self)
        stop(self)
        send(self, data)
        receive(self[, size=1])
    '''

    def __init__(self, mode, alsa_dev, baudrate=300, start=True):
        '''Initialize MiniModem class instance

        :param mode: str, operating mode of the minimodem application (see module constants)
        :param alsa_dev: str, ALSA device formated as 'card,device' (ex. '2,0')
        :param baudrate: int, baud rate of the modem (optional, default: 300)
        :param start: bool, start the modem subprocess on object instantiation (optional, default: True)

        :return: object, class instance

        :raises: ValueError, if mode is not one of the module constants (RX, TX)
        :raises: ProcessLookupError, if the minimodem application is not installed
        '''

        if mode in [RX, TX]:
            self.mode = mode
        else:
            raise ValueError('Unknown mode \'' + mode + '\', must be minimodem.RX or minimodem.TX')

        self.alsa_dev = alsa_dev
        self.baudrate = baudrate
        self.process = None
        self.shellcmd = None
        self.online = False

        try:
            # get full path of minimodem binary
            execpath = subprocess.check_output(['which', 'minimodem']).decode('utf-8').strip()
        except CalledProcessError:
            raise ProcessLookupError('minimodem application not installed, try: sudo apt install minimodem')

        if self.alsa_dev == None:
            # use system default audio device
            self.shellcmd = '%s --%s --quiet --print-filter %s' %(execpath, self.mode, self.baudrate)
        else:
            # use specified alsa audio device
            self.shellcmd = '%s --%s --quiet --alsa=%s --print-filter %s' %(execpath, self.mode, self.alsa_dev, self.baudrate)


        if start:
            self.start()

    def start(self):
        '''Start the modem by creating the appropriate subprocess with the given parameters'''
        if not self.online:
            # create subprocess with pipes for interaction with child process
            self.process = subprocess.Popen(self.shellcmd, shell=True, bufsize=-1, stdin=PIPE, stdout=PIPE, stderr=DEVNULL)
            self.online = True

    def stop(self):
        '''Stop the modem by terminating or killing the subprocess'''
        self.online = False
        # try to terminate normally
        self.process.terminate()
        # use a thread to communicate non-blocking-ly
        comm_thread = threading.Thread(target=self.process.communicate)
        comm_thread.daemon = True
        comm_thread.start()
        
        comm_start = time.time()
        comm_timeout = 5
        # manual timeout
        while time.time() < comm_start + comm_timeout:
            time.sleep(1)

        if self.process.poll() == None:
            # if the process still hasn't stopped, try to kill it
            self.process.kill()
            # use a thread to communicate non-blocking-ly
            comm_thread = threading.Thread(target=self.process.communicate)
            comm_thread.daemon = True
            comm_thread.start()

    def send(self, data):
        '''Send data to the underlying minimodem subprocess

        This method is only used with transmit mode (mode = minimodem.TX)

        :param data: bytes, byte string of data to send to the subprocess pipe
        '''
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def receive(self, size=1):
        '''Receive data from the underlying minimodem subprocess

        Reading from the subprocess.Popen.stdout pipe is blocking until the specified number of bytes is available.

        This method is only used with receive mode (mode = minimodem.RX)

        :param size: int, number of bytes to read from the subprocess pipe

        :return: bytes, received byte string of specified length
        '''
        return self.process.stdout.read(size)


class Modem:
    '''Create and manage MiniModem RX and TX instances to create a duplex soft modem

    Attributes:
    
        alsa_dev_in : str, input ALSA device formated as 'card,device' (ex. '2,0')
        alsa_dev_out : str, output ALSA device formated as 'card,device' (ex. '2,0')
        baudrate : int, baud rate of the modem
        _rx : object, instance of the MiniModem class
        _tx : object, instance of the MiniModem class
        rx_callback: func, received packet callback function with signature func(data) where data is type bytes
        MTU: int, maximum size of packet to be transmitted or received (default: 500, see Reticulum Network Stack)
        online: bool, status of the modem

    Methods:

        __init__(self[, alsa_dev_in=None, alsa_dev_out=None, baudrate=300, start=True])
        start(self)
        stop(self)
        send(self, data)
        set_rx_callback(callback)
        _receive(self[, size=1])
        _rx_loop(self)
    '''

    def __init__(self, alsa_dev_in=None, alsa_dev_out=None, baudrate=300, start=True):
        '''Initialize a Modem class instance

        :param alsa_dev_in: str, input ALSA device formated as 'card,device' (ex. '2,0') (optional, default: None)
        :param alsa_dev_out: str, output ALSA device formated as 'card,device' (ex. '2,0') (optional, default: None, if None alsa_dev_out is set to alsa_dev_in)
        :param baudrate: int, baud rate of the modem (optional, default: 300)
        :param start: bool, start the modem subprocess on object instantiation (optional, default: True)

        :return: object, class instance
        '''

        self.alsa_dev_in = alsa_dev_in
        self.alsa_dev_out = alsa_dev_out
        self.baudrate = baudrate
        self._rx = None
        self._tx = None
        self.rx_callback = None
        self.MTU = 500
        self.online = False

        # if a separate output device is not specified, assume it is the same as the input device
        if self.alsa_dev_out == None:
            self.alsa_dev_out = self.alsa_dev_in

        # create receive minimodem instance
        self._rx = MiniModem(RX, self.alsa_dev_in, baudrate=self.baudrate, start=False)
        # create transmit minimodem instance
        self._tx = MiniModem(TX, self.alsa_dev_out, baudrate=self.baudrate, start=False)

        # start the modem now if specified
        if start:
            self.start()

    def start(self):
        '''Start the modem by starting the underlying MiniModem instances and the receive loop thread'''
        self._rx.start()
        self._tx.start()
        self.online = True

        # start the receive loop as a thread since reads from the child process are blocking
        self._job_thread = threading.Thread(target=self._rx_loop)
        self._job_thread.daemon = True
        self._job_thread.start()

    def stop(self):
        '''Stop the modem by stopping the underlying MiniModem instances'''
        self.online = False
        # use a thread to stop the child process non-blocking-ly
        stop_tx_thread = threading.Thread(target=self._tx.stop)
        stop_tx_thread.daemon = True
        stop_tx_thread.start()
        # use a thread to stop the child process non-blocking-ly
        stop_rx_thread = threading.Thread(target=self._rx.stop)
        stop_rx_thread.daemon = True
        stop_rx_thread.start()

    def send(self, data):
        '''Send data to the underlying transmit MiniModem instance after wrapping data with HDLC flags

        :param data: bytes, byte string of data to send

        :raises: TypeError, if data is not type bytes
        '''
        if type(data) != bytes:
            raise TypeError('Modem data must be type bytes, ' + str(type(data)) + ' given.')
            return None

        # wrap data in start and stop flags
        data = HDLC.START + data + HDLC.STOP
        self._tx.send(data)

    def set_rx_callback(self, callback):
        '''Set receive callback function

        :param callback: func, function to call when packet is received (signature: func(data) where data is type bytes)
        '''
        self.rx_callback = callback

    def _receive(self):
        '''Get next byte from receive MiniModem instance

        Always call this function from a thread since the underlying subprocess pipe read will not return until data is available.

        Validation of the received byte is performed by attempting to decode the byte and catching any UnicodeDecodeError exceptions.

        :return: bytes, received byte string (could be  b'' if a decode error occured)
        '''
        data = self._rx.receive()

        # capture characters that cannot be decoded (receiver noise)
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            return b''
        
        return data

    def _rx_loop(self):
        '''Receive data into a buffer and find data packets

        The specified callback function is called once a complete packet is received.
        '''
        data_buffer = b''

        while self.online:
            # blocks until next character received
            data_buffer += self._receive()
            
            if HDLC.START in data_buffer:
                if HDLC.STOP in data_buffer:
                    # delimiters found, capture substring
                    start = data_buffer.find(HDLC.START) + len(HDLC.START)
                    end = data_buffer.find(HDLC.STOP, start)
                    if end > start:
                        data = data_buffer[start:end]
                        # remove received data from buffer
                        data_buffer = data_buffer[end + len(HDLC.STOP):]
                        
                        if len(data) <= self.MTU:
                            # under max packet length, receive data
                            if self.rx_callback != None:
                                self.rx_callback(data)
                        else:
                            # over max packet length, drop data
                            pass
                    else:
                        # partial packets causing mixed up delimiters,
                        # remove bad data from beginning of buffer
                        data_buffer = data_buffer[start + len(HDLC.START):]
                else:
                    if len(data_buffer) > self.MTU:
                        # no end delimiter and buffer length over max packaet size,
                        # remove data up to last start delimiter in buffer
                        data_buffer = data_buffer[data_buffer.rfind(HDLC.START):]
            else:
                # avoid missing start delimiter split over multiple loop iterations
                if len(data_buffer) > 10 * len(HDLC.START):
                    data_buffer = b''

            # simmer down
            time.sleep(0.1)



def get_alsa_device(device_desc, device_mode=RX):
    '''Get ALSA 'card,device' string based on device description

    The purpose of this function is to ensure the correct card and device are identified in case the connected audo devices change. The output of 'arecord -l' or 'aplay -l' (depending on specified device mode) is used to get device descriptions. Try running the applicable command (arecord or aplay) to find the device description.

    :param device_desc: str, unique string to search for in device descriptions (ex. 'USB PnP')
    :param device_mode: str, search for input or output audio devices (optional, default: minimodem.RX, see module constants)

    :return: str | None, card and device (ex. '2,0') or None if no matching device was found
    '''
    if device_mode == RX:
        alsa_cmd = ['arecord', '-l']
    elif device_mode == TX:
        alsa_cmd = ['aplay', '-l']
    else:
        raise Exception('Unknown mode \'' + device_mode + '\'')
        return None

    alsa_dev = None
    # get audio device descriptions
    alsa_devs = subprocess.check_output(alsa_cmd).decode('utf-8').split('\n')

    for line in alsa_devs:
        if device_desc in line:
            # if the specified description is found
            # capture the card number
            start = 'card'
            end = ':'
            start_index = line.find(start) + len(start)
            end_index = line.find(end, start_index)
            card = line[start_index:end_index].strip()
            # capture the device number
            start = 'device'
            end = ':'
            start_index = line.find(start) + len(start)
            end_index = line.find(end, start_index)
            device = line[start_index:end_index].strip()
            # build the device string
            alsa_dev = card + ',' + device
            break

    return alsa_dev





