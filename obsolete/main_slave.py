import time
import socket
import signal
import sys
import pylogix as pl
import logger as log  # Updated to match master code
import utils as ut    # Updated to match master code

host = '0.0.0.0'  # Listen on all available interfaces
port = 65410  # Same port as master

testing = True

# PLC TAGS
tag_init = 'RB_INIT'
tag_X = 'RB_501A_X'
ip_address = '192.168.168.46'
duration_tag = 'Program:RutinaAlternadorLineal.Fob1'


client = pl.PLC(ip_address)
client.SocketTimeout = 100

# SENSOR INPUTS
output_range = 10  # Select measurement range, options: 10g, 20g, 40g
sampling_rate = 1000  # Select sampling rate: 125, 250, 500, 1k, 2k, 4k
hpass_corner = 0  # Select high-pass filter corner: 0...6
duration = float(ut.read_plc_tag(client, duration_tag)) # Record length in seconds

# --- LOGGER INPUTS ---
save_every = 10000
child_script = "main/heartbeatA.py"



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
        connection, server_socket = ut.start_server(host, port)
    except Exception as e:
        print(f"Socket error: {e}")
        ut.cleanup(connection, server_socket, child_process)
        sys.exit(1)

    try:
        print('Waiting for folder and file names')
        folder_name = ut.receive_string(connection)
        file_name = ut.receive_string(connection)

    except Exception as e:
        print(f"Error receiving data: {e}")
        ut.cleanup(connection, server_socket, child_process)
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
        ut.cleanup(connection, server_socket, child_process)
        sys.exit(1)

    try:
        if not testing:
            ut.wait_for_plc(client, tag_init)
        sensor.current_t = time.time()
        print('Running!')
        sensor.run()

    except Exception as e:
        print(f"Communication error or sensor run error: {e}")
        ut.cleanup(connection, server_socket, child_process)
        sys.exit(1)

    except KeyboardInterrupt:
        ut.cleanup(connection, server_socket, child_process)
        sys.exit(0)

    finally:
        try:
            ut.cleanup(connection, server_socket, child_process)
        except NameError:
            print("Cleanup skipped: Some resources were not initialized.")
        
if __name__ == '__main__':
    main()
