# JoySendPy

A Python companion to [NetJoy](https://github.com/Qcent/NetJoy) for non-Windows machines. \
Requires PyGame and keyboard python modules. Install them with ```pip install -r requirements.txt``` 
\
```
python JoySender.py [OPTIONS] <ipaddress of host>
```

**Options:**

- `-n, --host <IP>`: Specifies the IP address of the host/server. Provide the IP address where you want to send the joystick data. This flag can be omitted.

- `-p, --port <PORT>`: Sets the port number to run JoySender on. Specify the port number for communication with the host/server. The default port is set to `5000`.

- `-f, --fps <FPS>`: Defines the communication frequency with the server in attempts per second. Set the desired frequency for communicating with the server. The default is `30` attempts per second.

- `-m, --mode <MODE>`: Sets the operational mode for JoySender. Use `1` for Xbox 360 emulation mode or `2` for DS4 emulation mode. Choose the desired mode based on your requirements. The default mode is Xbox 360 emulation.

- `-l, --latency`: Enables the display of latency output. Use this option if you want to see the latency information during communication. By default, this option is disabled.

- `-a, --auto`: Automatically selects the first joystick recognized by the system. If you have multiple joysticks connected, this option will automatically choose the first one. By default, this option is disabled.

- `-h, --help`: Displays the help message with information on how to use JoySender and its available options.

**Example Usage:**

To run JoySender with default settings, simply execute the following command, you will be prompted to enter a host address:

```
python JoySender.py
```

To specify the IP address and port of the host/server, type the ip and use the `-p/--port` option:

```
python JoySender.py 192.168.1.100 -p 8080
```

For DS4 emulation mode and latency output enabled, use the following command:

```
python JoySender.py -m 2 -l 
```

See [JoySender++ Readme](https://github.com/Qcent/NetJoy/blob/main/JoySender%2B%2B/README.md) for more usage instructions.

