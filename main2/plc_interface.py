import time  # Needed for time.sleep() in toggle_plc_tag()
import importlib.util  # Needed for dynamic loading of plc_config.py
from pylogix import PLC  # Needed to communicate with the PLC

class PLCInterface:
    def __init__(self, config_module):
        self._load_config(config_module)
        self.client = PLC()
        self.client.IPAddress = self.config['IP_ADDRESS']
        print(f'PLC Interface initialized with IP: {self.client.IPAddress}')
    
    def _load_config(self, config_module):
        spec = importlib.util.spec_from_file_location("plc_config", config_module)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        self.config = config.PLC_CONFIG  # Assumes PLC_CONFIG is a dictionary
        
    def read_plc_string_tag(self, tag):
        """ Reads a STRING (STR) tag from the PLC """        
        # Read string length
        length_response = self.client.Read(f"{tag}.LEN")
        
        if length_response.Status != 'Success' or length_response.Value is None:
            return None
        
        str_length = length_response.Value    
        if str_length == 0:
            return ""
        # Read string data (array of SINT)
        data_response = self.client.Read(f"{tag}.DATA[0]", str_length)  # Read multiple bytes
    
        if data_response.Status != 'Success' or data_response.Value is None:
            return None
        # Convert ASCII byte array to a Python string
        plc_string = ''.join(chr(c) for c in data_response.Value)
        
        return plc_string
        
    def read_plc_tag(self, tag):
        retries = self.config.get('TAG_RETRIES', 3)
        
        for _ in range(retries):
            response = self.client.Read(tag)
            try: 
                value = response.Value
                if value is not None:
                    print(f'Value found: {value}')
                    return value
            except:
                print('Error reading tag, retrying...')
                continue
        print(f'Failed to read {tag} after {retries} attempts.')
        return None
        
    def write_plc_tag(self, tag, value):
        """ Writes a value to a PLC tag """
        retries = self.config.get('TAG_RETRIES',3)
        for _ in range(retries):
            response = self.client.Write(tag, value)
            if response.Status == 'Success':
                print(f'✅ Successfully wrote {value} to {tag}')
                return
            else:
                print(f'❌ Write failed: {response.Status}')
                continue
        print(f'Failed to write {value} to {tag} after {retries} attempts')
        
    def wait_for_plc(self):
        print('Waiting for PLC')
        tag = self.config.get('TAG_INIT')
        while True:
            response = self.client.Read(tag)
            try:
                bool_val = bool(response.Value)
                if bool_val:
                    print('INIT!')
                    return
            except:
                print('Error reading tag, retrying...')
                continue
    
    def toggle_plc_tag(self, tag, duration=1):
        """ Toggles a boolean PLC tag ON, waits, then sets it OFF """
        self.write_plc_tag(tag, True)
        time.sleep(duration)
        self.write_plc_tag(tag, False)

    def disconnect(self):
        """ Closes the connection to the PLC """
        self.client.Close()
        print("🔌 PLC connection closed.")