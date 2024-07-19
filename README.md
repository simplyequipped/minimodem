# fskmodem
Python package for creating a full duplex audio frequency shift keying (AFSK) soft modem. 

## Reticulum

Use *fskmodem* with [Reticulum](https://github.com/markqvist/Reticulum) via the PipeInterface. See the Reticulum manual section on the [PipeInterface](https://markqvist.github.io/Reticulum/manual/interfaces.html#pipe-interface) for more information.

#### Reticulum Config Example #1
Default 300 baud modem, QDX audio device, QDX PTT via the *qdxcat* module, with a QDX radio frequency of 7.095 MHz:
```
  [[Pipe Interface]]
    type = PipeInterface
    enabled = True
    command = python3 -m fskmodem --rns --qdx 7095000
    bitrate = 300
```

#### Reticulum Config Example #2
500 baud modem, default audio device, no PTT:
```
  [[Pipe Interface]]
    type = PipeInterface
    enabled = True
    command = python3 -m fskmodem --baudmode 500 --rns
    bitrate = 500
```

Alternatively, use *fskmodem* as a KISS TNC with [Reticulum](https://github.com/markqvist/Reticulum) via the TCPClientInterface and the [tcpkissserver](https://github.com/simplyequipped/tcpkissserver) package. See [this gist](https://gist.github.com/simplyequipped/6c982ebb1ede6e5adfc149be15bbde6b) to get started quickly, and be sure to update the Reticulum config file accordingly.

## Command Line Interface (CLI)

A command line interface is available for the *fskmodem* module as of version 0.2.0. CLI usage:

```
USAGE: python -m fskmodem [OPTIONS]

OPTIONS:
--search-alsa-in
    ALSA audio input device search text
--search-alsa-out
    ALSA audio output device search text
--alsa-in
    ALSA audio input device formated as 'card,device'
--alsa-out
    ALSA audio output device formated as 'card,device'
--baudmode
    Baudmode of the modem, defaults to '300'
--sync-byte
    Suppress rx carrier detection until the specified ordinal byte value is received
--confidence
    Minimum confidence threshold based on SNR (i.e. squelch)', defaults to 1.5
--mark
    Mark frequency in Hz
--space
    Space frequency in Hz
--eom
    stdin end-of-message string, defaults to '\n\n' (not used with *--rns*)
--rns
    Use HDLC framing for RNS PipeInterface (*)
--quiet
    Do not print messages on start
--qdx
    Utilize qdxcat for PTT control of QRPLabs QDX radio, optionally followed by QDX frequency in Hz (**)
   

(*)  PipeInterface must be configured and enabled in the Reticulum config file.

(**) The qdxcat package must be installed to use --qdx options.
     If --qdx is specified and no audio devices are specified, --search_alsa_in is set to 'QDX'.
```

## Basic Usage
#### Example #1
```
import fskmodem

# use system default alsa audio device and modem defaults (300 baud)
modem = fskmodem.Modem()
modem.set_rx_callback(rx_func)

modem.send('hello world!')
```

#### Example #2
```
import fskmodem

def rx_callback(data):
    print(data)

# 1200 baud, start subprocesses later
modem = fskmodem.Modem(search_alsa_dev_in='USB PnP', baudrate=1200, start=False)
modem.set_rx_callback(rx_callback)
modem.start()

modem.send('hello world!')
```

## Install
Install the *fskmodem* package using pip:
```
pip3 install fskmodem
```

### Dependencies
The *minimodem* package is required and can be installed on Debian systems using apt:
```
sudo apt install minimodem
```

### Acknowledgements

The *minimodem* Unix application is developed by Kamal Mostafa
[http://www.whence.com/minimodem/](http://www.whence.com/minimodem/)
