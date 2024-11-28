import socket
import sys
import time
import pylogix as pl
import logger as log
import utils as ut
import numpy as np
import signal

# --- Slave ----
host = '192.168.168.67'  
port = 65410

testing = True

# --- PLC TAGS ---
tag_init = 'RB_INIT'
tag_X = 'RB_501B_X'
ip_address = '192.168.168.46'
duration_tag = 'Program:RutinaAlternadorLineal.Fob1'
frequency_tag = 'Program:RutinaAlternadorLineal.Fob1'

# Init PLC Com
client = pl.PLC(ip_address)
client.SocketTimeout = 100

# --- SENSOR INPUTS ---
output_range = 10         # Select measurement range, options: 10g, 20g, 40g
sampling_rate = 1000             # Select sampling rate: 125, 250, 500, 1k, 2k, 4k
hpass_corner = 0                # Select high-pass filter corner: 0...6
duration = float(ut.read_plc_tag(client, duration_tag)) # Record length in seconds


# --- LOGGER INPUTS ---
save_every = 1000

# --- Names ---
child_script = "heartbeatB.py"
folder_name = 'test'  
frequency = float(ut.read_plc_tag(client, frequency_tag))
file_name = str(frequency)
print(f'Trial name: {file_name}')

def main():
    try:
        child_process = ut.start_child_process(child_script)
    except Exception as e:
        print(f"Error starting heartbeat process: {e}")
        sys.exit(1)

    signal.signal(signal.SIGINT, ut.signal_handler)
    signal.signal(signal.SIGTERM, ut.signal_handler)

    print(f"Started heartbeat process with PID: {child_process.pid}")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))

    except socket.error as e:
        print(f"Socket error: {e}")
        ut.stop_child_process(child_process)
        sys.exit(1)
    
    try:
        ut.send_string(client_socket, folder_name)  
        ut.send_string(client_socket, file_name)

    except Exception as e:
        print(f"Error sending data: {e}")
        client_socket.close()
        ut.stop_child_process(child_process)
        sys.exit(1)

    try:
        print('Init Logger')
        sensor = log.AccelerometerLogger(file_name,
                                         folder_name,
                                         save_every,
                                         client,
                                         tag_X,
                                         output_range=output_range,         
                                         hpass_corner=hpass_corner,               
                                         duration=duration,
                                         sampling_rate=sampling_rate) 
        sensor.calibrate()
        sensor.send_after_calib()

    except Exception as e:
        print(f"Sensor initialization or calibration error: {e}")
        client_socket.close()
        ut.stop_child_process(child_process)
        sys.exit(1)

    try:
        if not testing:
            ut.wait_for_plc(client, tag_init)
        sensor.current_t = time.time()
        print('Running!')
        sensor.run()

    except Exception as e:
        print(f"Communication error or sensor run error: {e}")
        ut.stop_child_process(child_process)
        sys.exit(1)

    except KeyboardInterrupt:
        ut.stop_child_process(child_process)
        sys.exit(0)

    finally:
        ut.cleanup(connection, server_socket, child_process)

if __name__ == '__main__':
    main()

