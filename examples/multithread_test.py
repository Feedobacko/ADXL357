import threading
import queue
import time
import csv
import numpy as np
import sys
sys.path.append("../")
from ADXL357 import ADXL357


# --- Global Configuration ---
SAMPLING_RATE = 2000  # Hz
WINDOW_SIZE = 100  # Samples for RMS calculation
SAVE_INTERVAL = 1000  # Samples to save in a chunk
PLC_UPDATE_INTERVAL = 0.1  # Seconds between RMS updates to PLC
THRESHOLD = 5.0  # Acceleration threshold for alerts

# Shared buffers
data_queue = queue.Queue(maxsize=SAVE_INTERVAL * 2)  # Holds raw data for saving
rms_queue = queue.Queue(maxsize=10)  # Holds RMS values for PLC communication

# Sensor setup
sensor = ADXL357()
sensor.setrange(10)
sensor.setfilter(SAMPLING_RATE, 0)
sensor.start()

# --- Sampling Task ---
def sampling_task():
    print("Starting sampling task...")
    while True:
        x, y, z = sensor.get_axis()
        data_queue.put((time.time(), x, y, z))  # Add timestamped data to the queue

# --- RMS Calculation & PLC Communication Task ---
def rms_and_plc_task():
    print("Starting RMS and PLC communication task...")
    buffer = []  # Local buffer for RMS calculation
    while True:
        # Collect data for RMS calculation
        while len(buffer) < WINDOW_SIZE:
            try:
                _, x, y, z = data_queue.get(timeout=0.1)
                buffer.append((x, y, z))
            except queue.Empty:
                continue

        # Calculate RMS
        buffer_np = np.array(buffer[-WINDOW_SIZE:])  # Use the last WINDOW_SIZE samples
        rms_x = np.sqrt(np.mean(buffer_np[:, 0] ** 2))
        rms_y = np.sqrt(np.mean(buffer_np[:, 1] ** 2))
        rms_z = np.sqrt(np.mean(buffer_np[:, 2] ** 2))
        rms_queue.put((rms_x, rms_y, rms_z))  # Add RMS to the RMS queue

        # Check for threshold violations
        if max(rms_x, rms_y, rms_z) > THRESHOLD:
            print(f"Threshold exceeded: RMS=[{rms_x:.2f}, {rms_y:.2f}, {rms_z:.2f}]")

        # Simulate PLC communication
        print(f"Sending RMS to PLC: RMS=[{rms_x:.2f}, {rms_y:.2f}, {rms_z:.2f}]")
        send_values = [rms_x, rms_y, rms_z]
        try:
            self.client.Write(self.tag_X, send_values)
        except Exception as e:
            print(f'Failed to send values of acceleration: {e}')
            
        time.sleep(PLC_UPDATE_INTERVAL)

# --- Data Saving Task ---
def data_saving_task():
    print("Starting data saving task...")
    with open("vibration_data.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "accel_x", "accel_y", "accel_z"])  # CSV header

        while True:
            chunk = []
            while len(chunk) < SAVE_INTERVAL:
                try:
                    chunk.append(data_queue.get(timeout=0.1))
                except queue.Empty:
                    continue
            writer.writerows(chunk)
            file.flush()  # Ensure data is written to disk

# --- Main ---
if __name__ == "__main__":
    # Create and start threads
    sampling_thread = threading.Thread(target=sampling_task, daemon=True)
    rms_thread = threading.Thread(target=rms_and_plc_task, daemon=True)
    saving_thread = threading.Thread(target=data_saving_task, daemon=True)

    sampling_thread.start()
    rms_thread.start()
    saving_thread.start()

    try:
        while True:
            time.sleep(1)  # Keep main thread alive
    except KeyboardInterrupt:
        print("Shutting down...")
        sensor.stop()
