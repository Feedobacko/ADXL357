import time
import sys
import numpy as np
import matplotlib.pyplot as plt
import scipy.signal as signal
sys.path.append("../")
from ADXL357 import ADXL357

# --- INPUTS ---
output_range = 10         # Select measurement range
sampling_rate = 1000             # Select sampling rate
hpass_corner = 0                # Select high-pass filter corner
duration = 10                   # Record lenght as second


# --- VARIABLES ---
interval = 1 / sampling_rate                    # Interval as second
npts = int(duration * sampling_rate)              # Number of data points
fn = sampling_rate / 2                            # Nyquist frequency
t = np.linspace(0, duration, npts)                # Create time domain
data = np.zeros((3, npts), dtype = np.float64)    # Create an empty array


# --- SET ADXL357 PARAMETERS ---
adxl357 = ADXL357()
adxl357.setrange(output_range)                    # Set measurement range
adxl357.setfilter(sampling_rate, hpass_corner)    # Set data rate and filter properties 
adxl357.start()                                   # Enable measurement mode
time.sleep(0.1)                                   # Wait briefly until the sensor is ready

adxl357.calibrate()
# --- READING LOOP ---
print("Recording...")
start = time.time()
for i in range(npts):
    x,y,z = adxl357.get_axis()
    data[:,i] = [x,y,z]
end = time.time()

adxl357.stop()          # Enable standby mode
print(f"Elapsed Time : {round((end-start),2)} second \n")


# --- SAVE TO CSV FILE ---
print("Writing csv file...\n")
fcsv = open("test_adxl357.csv", "w")
for i in range(npts):
    fcsv.write(f"{data[0][i]}, {data[1][i]}, {data[2][i]}\n")
    fcsv.flush()

    
# --- PLOT ---
print("Plotting...")
label = ["X", "Y", "Z"]
color = ["Blue","Red","Green"]

fig, (ax1, ax2) = plt.subplots(2,1)
fig.subplots_adjust(hspace=0.4)

for i in range(3):
    ax1.plot(t, data[i], lw=1, color=color[i], label=label[i])
    
    frq, amp = signal.periodogram(data[i], sampling_rate, scaling="density")
    ax2.plot(frq, amp, lw=1, color=color[i], label=label[i])
    

ax1.set_xlabel("Time [s]")
ax1.set_ylabel("Acceleration [g]")
ax1.legend(prop={"size":8})
ax1.grid()

ax2.set_xlabel("Frequency [Hz]")
ax2.set_ylabel(r"PSD [$g^{2}/Hz$]")
ax2.legend(prop={"size":8})
ax2.grid()

plt.show()
