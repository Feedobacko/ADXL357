import struct
import socket
import subprocess
import sys

def cleanup(connection, server_socket, child_process):
    connection.close()
    server_socket.close()
    stop_child_process(child_process)
    
def handle_exception(e, connection, server_socket, child_process):
    print(e)
    connection.close()
    server_socket.close()
    stop_child_process(child_process)
    sys.exit(1)
    
def send_float(client_socket, data):
    try:
        packed_data = struct.pack('>3f', *data)
        client_socket.sendall(packed_data)
    except Exception as e:
        print(f"Error sending data: {e}")
        
def send_string(client_socket, data):
    # Encode the string into bytes
    encoded_data = data.encode('utf-8')
    # Create a TCP/IP socket
    try:
        client_socket.sendall(encoded_data)
    except Exception as e:
        raise RuntimeError(f'Error sending string: {e}')
        
def start_server(host, port):
    # Create a TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")
    connection, client_address = server_socket.accept()
    return connection, server_socket

def receive_data(connection, buffer=12):
    data = connection.recv(buffer)  # Expecting to receive 12 bytes for 3 floats
    if data:
        if len(data) == 12:  # Check if received data is exactly 12 bytes
            received_floats = struct.unpack('>3f', data)
            #print(f"Received floats: {received_floats}")
            return received_floats
        else:
            print("Error: Received incorrect number of bytes")
            return None
    else:
        print("Error: Timeout")
        return None

def receive_string(connection):
    data = connection.recv(1024)  # Expecting to receive 12 bytes for 3 floats
    if data:  # Check if received data is exactly 12 bytes
        received_string = data.decode('utf-8')
        print(f"Received string: {received_string}")
        return received_string
    else:
        print("Error: Timeout")
        return None
    
def start_child_process(script_path):
    process = subprocess.Popen([sys.executable, script_path])
    return process

def stop_child_process(process):
    process.terminate()
    try:
        process.wait(timeout = 1)
    except subprocess.TimeoutExpired:
        process.kill()
    
def signal_handler(sig, frame):
    print("Stopping child process...")
    stop_child_process(child_process)
    sys.exit(0)


def read_plc_tag(client, tag):
    print(f'Reading PLC TAG: {tag}')
    while True:
        response = client.Read(tag)
        try: 
            value = response.Value
            if value is not None:
                print(f'Value found: {value}')
                return value
        except:
            continue
    
def wait_for_plc(client, tag):
    print('Waiting for PLC')
    while True:
        response = client.Read(tag)
        try:
            bool_val = bool(response.Value)
            if bool_val:
                print('INIT!')
                return
        except:
            continue
    return