CONFIG = {
    "HOST": "192.168.168.32",
    "PORT": 65410,
    "SAMPLING_RATE": 2000,  # Hz
    "WINDOW_SIZE": 100,  # Samples for RMS calculation
    "SAVE_INTERVAL": 10000,  # Samples per chunk
    "PLC_UPDATE_INTERVAL": 0.0001,  # Seconds between RMS updates
    "THRESHOLD": 100.0,  # Acceleration threshold for alerts
    "TESTING": True,  # Set to False for actual PLC operation
    "FOLDER_NAME": "data_060325"
}