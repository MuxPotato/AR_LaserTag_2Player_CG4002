# Source code structure
## `beetle.py`: 
- Contains base Beetle class and individual classes that extend Beetle to provide gun, glove and vest functionality

## `ble_delegate.py`: 
- Contains bluepy Delegate used to receive data from Beetle

## `external_main.py`: 
- Runs both internal and external code to transmit and receive data from all the Beetles involved
- This is the code to run and start all the comms protocols running

## `external_utils.py`: 
- Provides helper functions, constants, structs needed for external comms logic

## `imu_data_collector.py`: 
- Basic code to collect IMU data from a specified Beetle and write collected data to a csv file
- Update the IMU_BEETLE variable inside it to your Beetle's Bluetooth MAC address

## `internal_main.py`: 
- Main thread for the internal comms protocol
- `external_main.py` automatically initialises the main thread and runs it to connect to all Beetles involved

## `internal_utils.py`: 
- Provides helper functions, constants, structs needed for internal comms logic

## `relay_client.py`: 
- Relay client that connects to relay server(running on the Ultra96) to send raw data from Beetle to the server and update the Beetles involved with the latest game state

# Quick start
- Run `python3 external_main.py` without any arguments to start all the necessary threads and run the comms protocols
- To end transmission and quit, press `CTRL+C` and wait for all threads to terminate

