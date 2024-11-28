import subprocess
import signal
import sys
import time
import os
import pylogix as pl

def ping_plc(comm, tag, ms = 100):
    current_t = time.perf_counter()
    value = True
    t = 0
    counter = 0
    s = ms/1000
    while True:
        act_time = time.perf_counter()
        comm.Write(tag, int(value))
        time.sleep(s)
        value = not value
        counter += 1
        
        if counter%(s) == 0:
            dt = act_time - current_t
            t += dt
            current_t = act_time
            
        if counter%100 == 0:
            print('Counter: {}, Total elapsed Time: {}, dt: {}'.format(counter, t, dt))
        
if __name__ == "__main__":
    try:
        tag = 'RB_501A_HB'#RaspberryNormal'
        ip_address = '192.168.168.46'
        ms = 500
        with pl.PLC(ip_address) as comm:
            ping_plc(comm, tag ,ms)
            
    except KeyboardInterrupt:
        print("Child process interrupted and stopping...")
    finally:
        print("Stopped")
