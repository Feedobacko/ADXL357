import threading
import queue
import time
import csv
import numpy as np
import os
import sys
sys.path.append("../")

from ADXL357 import ADXL357
from plc_interface import PLCInterface  # Import PLC class
from config import CONFIG
import utils as ut


class VibrationMonitor:
    def __init__(self, plc_config):
        """Initialize the vibration monitoring system."""
        self.host = CONFIG["HOST"]
        self.port = CONFIG["PORT"]
        self.sampling_rate = CONFIG["SAMPLING_RATE"]
        self.window_size = CONFIG["WINDOW_SIZE"]
        self.save_interval = CONFIG["SAVE_INTERVAL"]
        self.plc_update_interval = CONFIG["PLC_UPDATE_INTERVAL"]
        self.threshold = CONFIG["THRESHOLD"]
        self.testing = CONFIG["TESTING"]
        self.folder_name = CONFIG["FOLDER_NAME"]

        # Init PLC Interface
        self.plc = PLCInterface(plc_config)

        # Read PLC values
        self.frequency = float(self.plc.read_plc_tag(self.plc.config.get("TAG_FREQUENCY", 0)))

        # Define file name
        self.file_name = f"{self.frequency}hz"

        # Shared buffers
        self.data_queue = queue.Queue(maxsize=self.save_interval * 2)  # Holds raw data
        self.rms_queue = queue.Queue(maxsize=100)  # Holds RMS values for PLC

        # Logging state
        self.is_logging = True  # Start with logging on
        self.vdf_running = False

        # Read PLC string ID
        self.id = self.plc.read_plc_string_tag(self.plc.config.get('TAG_ID_PRUEBA', 'NO_ID_FOUND'))
        print(f'🔹 Test ID: {self.id}') 
        
        # Sensor setup
        self.sensor = ADXL357.ADXL357()
        self.sensor.setrange(10)
        self.sensor.setfilter(self.sampling_rate, 0)

    def check_if_running(self):
        """Check VDF status and control logging state."""
        tag = self.plc.config.get('VDF_STATUS', 0)
        value = self.plc.read_plc_tag(tag)
        if value == 2:
            self.vdf_running = True
            
        if self.vdf_running and value != 2:
            self.vdf_running = False
            self.is_logging = False
            
    def sampling_task(self):
        """Continuously sample accelerometer data and add to queue."""
        print("📡 Starting sampling task...")
        start_time = time.time()
        self.sensor.start()

        while True:
            x, y, z = self.sensor.get_axis()
            self.data_queue.put((time.time() - start_time, x, y, z))

    def rms_and_plc_task(self):
        """Compute RMS and send to PLC."""
        print("📊 Starting RMS & PLC communication task...")

        while True:
            buffer = []
            # Collect data for RMS
            while len(buffer) < self.window_size:
                try:
                    t, x, y, z = self.data_queue.get(timeout=0.1)
                    buffer.append((x, y, z))
                except queue.Empty:
                    continue

            # Calculate RMS
            buffer_np = np.array(buffer[-self.window_size:])
            t = float(t)
            rms_x = float(np.sqrt(np.mean(buffer_np[:, 0] ** 2)))
            rms_y = float(np.sqrt(np.mean(buffer_np[:, 1] ** 2)))
            rms_z = float(np.sqrt(np.mean(buffer_np[:, 2] ** 2)))
            #self.rms_queue.put((rms_x, rms_y, rms_z))

            # Threshold check
            if max(rms_x, rms_y, rms_z) > self.threshold:
                print(f"⚠️ Threshold exceeded: RMS=[{rms_x:.2f}, {rms_y:.2f}, {rms_z:.2f}]")
            # Send to PLC
            try:
                send_values = [t, rms_x, rms_y, rms_z]
                print(f'Trying to write rms: {send_values}')
                self.plc.client.Write(self.plc.config.get('TAG_X', 0), send_values)
                
            except Exception as e:
                print(f'❌ Failed to send RMS values to PLC: {e}')

            time.sleep(self.plc_update_interval)

    def data_saving_task(self):
        """Save data to CSV periodically."""
        print("💾 Starting data saving task...")
        os.makedirs(self.folder_name, exist_ok=True)
        with open(f"{self.folder_name}/{self.file_name}.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["timestamp", "accel_x", "accel_y", "accel_z"])  # CSV header
            while True:
                chunk = []
                while len(chunk) < self.save_interval:
                    try:
                        chunk.append(self.data_queue.get(timeout=0.1))
                    except queue.Empty:
                        continue
                writer.writerows(chunk)
                file.flush()

    def heartbeat_task(self):
        print('Starting heartbeat')
        try:
            tag = self.plc.config.get('TAG_HEARTBEAT', None)
            if not tag:
                print("❌ Heartbeat tag not found in PLC configuration.")
                return
            ms = 500
            s = ms/1000
            value = True
            while True:
                self.plc.client.Write(tag, int(value))
                time.sleep(s)
                value = not value  # Toggle value
        except KeyboardInterrupt:
            print("Child process interrupted and stopping...")
        finally:
            print("Stopped")
            
    def run(self):
        """Start all system threads."""
        # Start Threads
        sampling_thread = threading.Thread(target=self.sampling_task, daemon=True)
        rms_thread = threading.Thread(target=self.rms_and_plc_task, daemon=True)
        saving_thread = threading.Thread(target=self.data_saving_task, daemon=True)
        heartbeat_thread = threading.Thread(target=self.heartbeat_task, daemon=True)  
        heartbeat_thread.start()

        self.plc.wait_for_plc()

        sampling_thread.start()
        rms_thread.start()
        saving_thread.start()
        
        start_time = time.time()
        try:
            while True:
                if self.is_logging:
                    self.check_if_running()
                else:
                    print("⛔ Shutting down...")
                    self.sensor.stop()
                    break

            print(f"✅ Test finished, duration: {time.time() - start_time:.2f} seconds.")
            
        except KeyboardInterrupt:
            print("⛔ Shutting down...")
            self.sensor.stop()


# --- Main Execution ---
if __name__ == "__main__":
    # Check if a PLC config file was provided in the command line
    if len(sys.argv) < 2:
        print("❌ Error: No PLC configuration file provided.")
        print("Usage: python vibration_monitor.py <plc_config_file>.py")
        sys.exit(1)

    plc_config_file = sys.argv[1]  # Get the PLC config filename from command line
    print(f"🔧 Using PLC configuration: {plc_config_file}")

    monitor = VibrationMonitor(plc_config_file)
    monitor.run()