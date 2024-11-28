"""
Python module for interfacing Analog Devices ADXL357 accelererometer through SPI
bus with the Raspberry Pi. A clone from https://github.com/kamerozdmr/PiADXL355
changing some definitions to fit my purposes. Thanks!
"""

import spidev
import time
import RPi.GPIO as GPIO
from ADXL357_definitions import *

class ADXL357():
    def __init__(self):
        # SPI init
        self.spi = spidev.SpiDev()
        self.spi.open(SPI_BUS, SPI_DEVICE)
        self.spi.max_speed_hz = SPI_MAX_CLOCK_HZ
        self.spi.mode = SPI_MODE

        GPIO.setmode(GPIO.BOARD)                  # Use physical pin numbers
        self.drdy_pin = DRDY_PIN                # Define Data Ready pin
        self.drdy_delay = DRDY_DELAY            # Define Data Ready delay
        self.drdy_timeout = DRDY_TIMEOUT        # Define Data Ready timeout
        
        if self.drdy_pin is not None:
            GPIO.setup(self.drdy_pin, GPIO.IN)
        
        # Default device parameters
        RANGE = 10
        ODR   = 1000
        HPFC  = 0
        
        # Device init
        self.transfer = self.spi.xfer2
        self.setrange(RANGE)                    # Set default measurement range
        self.setfilter(ODR, HPFC)               # Set default ODR and filter props
        self.wait_drdy()

        self.factor = RANGE_TO_SENSITIVITY[RANGE]   # Instrument factor raw to g [not accurate]
        
        self.offsets = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.reset_offsets()
        
    def read(self, register, length=1):
        address = (register << 1) | 0b1
        if length == 1:
            result = self.transfer([address, 0x00])
            return result[1]
        else:
            result = self.transfer([address] + [0x00] * (length))
            return result[1:]

    def write(self, register, value):
        # Shift register address 1 bit left, and set LSB to zero
        address = (register << 1) & 0b11111110
        result = self.transfer([address, value])
    
    def wait_drdy(self):
        start = time.time()
        elapsed = time.time() - start
        # Wait DRDY pin to go low or DRDY_TIMEOUT seconds to pass
        if self.drdy_pin is not None:
            drdy_level = GPIO.input(self.drdy_pin)
            while (drdy_level == GPIO.LOW) and (elapsed < self.drdy_timeout):
                elapsed = time.time() - start
                drdy_level = GPIO.input(self.drdy_pin)
                # Delay in order to avoid busy wait and reduce CPU load.
                time.sleep(self.drdy_delay)
                #self.wait2go_low()
            if elapsed >= self.drdy_timeout:
                print("\nTimeout while polling DRDY pin")
        else:
            time.sleep(self.drdy_timeout)
            print("\nDRDY pin did not connected")

    def wait2go_low(self):
        drdy_level = GPIO.input(self.drdy_pin)
        while (drdy_level == GPIO.HIGH):
            drdy_level = GPIO.input(self.drdy_pin)
            time.sleep(self.drdy_delay)
    
    def fifofull(self):
        return self.read(REG_STATUS) & 0b10

    def fifooverrange(self):
        return self.read(REG_STATUS) & 0b100
    
    def start(self):
        tmp = self.read(REG_POWER_CTL)
        self.write(REG_POWER_CTL, tmp & 0b0)

    def stop(self):
        tmp = self.read(REG_POWER_CTL)
        self.write(REG_POWER_CTL, tmp | 0b1)  
    
    def conversion(self, value):
        if (0x80000 & value):
            ret = - (0x0100000 - value)
            """Convversion function from EVAL-ADICUP360 repository"""
        else:
            ret = value
        return ret
    
    def setrange(self, r):
        self.stop()
        temp = self.read(REG_RANGE)
        self.write(REG_RANGE, (temp & 0b11111100) | RANGE_TO_BIT[r])
        self.factor = 1 / RANGE_TO_SENSITIVITY[r]  # Use sensitivity for scaling
        self.start()

    def setfilter(self, lpf, hpf):
        self.stop()
        self.write(REG_FILTER, (HPFC_TO_BIT[hpf] << 4) | ODR_TO_BIT[lpf])
        self.start()
    
    def get_x_raw(self):
        datal = self.read(REG_XDATA3, 3)
        low = (datal[2] >> 4)
        mid = (datal[1] << 4)
        high = (datal[0] << 12)
        res = low | mid | high
        res = self.conversion(res)
        return res

    def get_y_raw(self):
        datal = self.read(REG_YDATA3, 3)
        low = (datal[2] >> 4)
        mid = (datal[1] << 4)
        high = (datal[0] << 12)
        res = low | mid | high
        res = self.conversion(res)
        return res

    def get_z_raw(self):
        datal = self.read(REG_ZDATA3, 3)
        low = (datal[2] >> 4)
        mid = (datal[1] << 4)
        high = (datal[0] << 12)
        res = low | mid | high
        res = self.conversion(res)
        return res

    def get_x(self):
        return float(self.get_x_raw()) * self.factor

    def get_y(self):
        return float(self.get_y_raw()) * self.factor
    
    def get_z(self):
        return float(self.get_z_raw()) * self.factor

    def get_3_v_fifo(self):
        res = []
        x = self.read(REG_FIFO_DATA, 3)
        while(x[2] & 0b10 == 0):
            y = self.read(REG_FIFO_DATA, 3)
            z = self.read(REG_FIFO_DATA, 3)
            res.append([x, y, z])
            x = self.read(REG_FIFO_DATA, 3)
        return res

    def convert_raw_to_g(self, data):
        """Convert a list of raw style samples into g values"""
        res = [[d[0] * self.factor, d[1] * self.factor, d[2] * self.factor] for d in data]
        return res

    def get_axis_raw(self):
        self.wait_drdy()
        return self.get_x_raw(), self.get_y_raw(), self.get_z_raw()
    
    def get_axis(self):
        self.wait_drdy()
        x = self.get_x() - self.offsets['x']
        y = self.get_y() - self.offsets['y']
        z = self.get_z() - self.offsets['z']
        return x, y, z
    
    def calibrate(self, samples=100):
        sum_x, sum_y, sum_z = 0.0, 0.0, 0.0

        for _ in range(samples):
            x, y, z = self.get_axis()  # Read scaled values in g
            sum_x += x
            sum_y += y
            sum_z += z
            time.sleep(0.01)  # Small delay between samples to avoid overwhelming the sensor

        # Calculate average offsets
        self.offsets['x'] = sum_x / samples
        self.offsets['y'] = sum_y / samples
        self.offsets['z'] = (sum_z / samples) - 1.0  # Subtract 1 g for Z-axis gravity

        print(f"Calibration complete: Offsets (g) -> X: {self.offsets['x']}, "
              f"Y: {self.offsets['y']}, Z: {self.offsets['z']}")
        return self.offsets
        
    
    def reset_offsets(self):
        # Write 0 to all offset registers
        self.write(REG_OFFSET_X_H, 0x00)
        self.write(REG_OFFSET_X_L, 0x00)
        
        self.write(REG_OFFSET_Y_H, 0x00)
        self.write(REG_OFFSET_Y_L, 0x00)
        
        self.write(REG_OFFSET_Z_H, 0x00)
        self.write(REG_OFFSET_Z_L, 0x00)

        # Print confirmation
        print("All offsets reset to 0!")
