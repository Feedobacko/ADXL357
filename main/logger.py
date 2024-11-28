import os
import time
import numpy as np
import csv
from datetime import datetime
import sys
sys.path.append("../")
from ADXL357 import ADXL357

class AccelerometerLogger():
    def __init__(self, file_name, folder_name, save_every, client, tag_X, n_history=500, desired_hz=200,
                 output_range=10,
                 hpass_corner=0,
                 duration=10,
                 sampling_rate=1000):
        
        self.file_name = file_name
        self.folder_name = folder_name
        self.desired_hz = desired_hz  # Desired sample rate in Hz
        self.interval = 1 / desired_hz
        
        self.count = 0
        self.N = save_every
        self.lims = 10
        self.current_t = 0
        self.t = 0
        self.dt = 0
        self.last_save_t = 0
        self.history_index = 0
        self.i = 0
        self.security_interval = 5  # Default value

        self.sensor = ADXL357.ADXL357()
        self.sensor.setrange(output_range)
        self.sensor.setfilter(sampling_rate, hpass_corner)
        self.sensor.start()           
        
        self.client = client
        self.tag_X = tag_X
        self.n_history = n_history

        # Pre-allocate arrays
        self.X_history = np.zeros(save_every)
        self.Y_history = np.zeros(save_every)
        self.Z_history = np.zeros(save_every)
        self.t_history = np.zeros(save_every)
        
        self.X_history2 = np.zeros(n_history)
        self.Y_history2 = np.zeros(n_history)
        self.Z_history2 = np.zeros(n_history)
        
        self.ax_rms = 0
        self.ay_rms = 0
        self.az_rms = 0
        self.start_time = time.perf_counter()
        self.initialize_csv_file()
    
    def calibrate(self):
        for _ in range(3):
            print('----- Calibrating -----')
            calibrated_values = self.sensor.calibrate()
            self.x_offset = calibrated_values['x']
            self.y_offset = calibrated_values['y']
            self.z_offset = calibrated_values['z']

            if self.x_offset != 0.0 and self.y_offset != 0.0 and self.z_offset != 0.0:
                break
        else:
            print('Calibration failed after multiple attempts.')
        
    def send_after_calib(self):
        self.update_values()
        self.send_accel()
        
    def add_to_time(self):
        act_time = time.perf_counter()
        dt = act_time - self.current_t
        self.t = act_time - self.start_time
        self.dt = dt
        self.current_t = act_time
        
    def update(self):
        self.update_values()
        self.i += 1
        if self.t > 1 and self.i % self.security_interval == 0:
            self.send_accel()

    def send_accel(self):
        send_values = [self.t, self.ax_rms, self.ay_rms, self.az_rms]
        try:
            self.client.Write(self.tag_X, send_values)
        except Exception as e:
            print(f'Failed to send values of acceleration: {e}')
      
    def calc_rms(self, data_array):
        squared = data_array ** 2
        mean_squared = np.mean(squared)
        return np.sqrt(mean_squared)

    def update_values(self):
        self.count += 1
        self.X, self.Y, self.Z = self.sensor.get_axis()
        self.add_to_time()
    
        # Save current values to the primary history arrays
        self.X_history[self.history_index] = self.X
        self.Y_history[self.history_index] = self.Y
        self.Z_history[self.history_index] = self.Z
        self.t_history[self.history_index] = self.t
    
        # Update secondary history arrays (circular buffer)
        buffer_index = self.history_index % self.n_history
        self.X_history2[buffer_index] = self.X
        self.Y_history2[buffer_index] = self.Y
        self.Z_history2[buffer_index] = self.Z
    
        # Calculate RMS using the full circular buffer
        self.ax_rms = self.calc_rms(self.X_history2)
        self.ay_rms = self.calc_rms(self.Y_history2)
        self.az_rms = self.calc_rms(self.Z_history2)
    

        # Save data to CSV when full
        if self.count == self.N:
            self.save_data_to_csv()
            self.count = 0
            
        # Increment history index and wrap around for primary arrays
        self.history_index += 1


    def save_data_to_csv(self):
        dt = np.round(self.current_t - self.last_save_t, 2)
        Hz = np.round(self.N / dt, 1)
        print(f"Writing to csv {self.file_name}, at time {np.round(self.t, 2)} sec, dt: {dt}s, Hz: {Hz}")
        
        # Save only the filled portion of the history arrays
        data_to_write = np.column_stack((
            self.t_history,
            self.X_history,
            self.Y_history,
            self.Z_history
        ))
        
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data_to_write)
        
        self.clear_history()
    
    def clear_history(self):
        self.history_index = 0

    def run(self):
        self.start_time = time.perf_counter()  # Reset start time for logging
        self.current_t = self.start_time       # Ensure current time is reset as well
        self.t = 0                             # Start the time tracking from 0
        while True:
            start_time = time.perf_counter()  # Record the start time of each sample
            self.update()
            elapsed_time = time.perf_counter() - start_time
            time_to_sleep = self.interval - elapsed_time
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)
        
    def initialize_csv_file(self):
        # Create the 'accel data' folder if it doesn't exist
        folder_path = os.path.join(os.getcwd(), self.folder_name)
        os.makedirs(folder_path, exist_ok=True)

        # Create the file name based on the current date and time of program start
        start_time = datetime.now()
        file_name = self.file_name + "_" + start_time.strftime("%d-%m-%y_%H-%M.csv")
        self.file_path = os.path.join(folder_path, file_name)

        # Write headers to the CSV file
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['time', 'accel_x', 'accel_y', 'accel_z'])
