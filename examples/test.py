import sys
import time
sys.path.append("../")
from CEDAS_ACC_library import ADXL355

# --- INPUTS ---
output_range = 10#2.048            # Select measurement range
sampling_rate = 125             # Select sampling rate
hpass_corner = 0                # Select high-pass filter corner
duration = 20                   # Record lenght as second


# --- VARIABLES -


# --- SET ADXL355 PARAMETERS ---
adxl355 = ADXL355()
adxl355.setrange(output_range)                    # Set measurement range
adxl355.setfilter(sampling_rate, hpass_corner)    # Set data rate and filter properties 
adxl355.start()                                   # Enable measurement mode
time.sleep(0.1)

for i in range(1000):
    x,y,z = adxl355.getAxis()
    print(x,y,z)