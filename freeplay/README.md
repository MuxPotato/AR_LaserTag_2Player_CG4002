
## RelayServer.py
Receives data from gun, vest, ankle, and glove beetles through RelayClient. Sends the data to both AI threads through respective P1 and P2 IMU queues. Also sends whether the player is shot to the game engine thread. Sends hp and bullets back to RelayClient to update beetles.

## AIOne.py
Sends IMU data for prediction for player 1 and sends `action:player_id` through `P1_action_queue` to the game engine once received. Sends field of view query to MQTT client through `viz_queue`.

## AITwo.py
Sends IMU data for prediction for player 2 and sends `action:player_id` through `P2_action_queue` to the game engine once received. Sends field of view query to MQTT client through `viz_queue`.

## AIPredictor.py 
Predicts the action based on the IMU data 

## GameEngine.py
Receives action from AI. Receives field of view from phone through MQTT. Calculates game state. Updates phones through MQTT and beetles through RelayServer thread.

## MQTT.py
Gets data from `viz_queue` and publishes it in the `gamestate` topic. Receives response (hit or miss information) from the phone in the `response` topic. Sends response back to the game engine through the respective player response queue.

## Color.py 
Makes the printed output of each thread a different color for easy distinguishing 

# Setup

1. **Run the MQTT broker**:
   - SSH into Ultra96:
     ```bash
     su -
     ```
   - Enter the password, then:
     ```bash
     cd /home/xilinx/unityMQTT/hivemq-ce-2024.7/bin
     chmod 755 run.sh
     ./run.sh
     ```
   - Wait for the message: `INFO - Started TCP Listener on address 0.0.0.0 and on port 1883`.

3. **Run the Ultra96 threads**:
   - Open another terminal:
     ```bash
     su -
     ```
   - Enter the password, then:
     ```bash
     cd /home/xilinx/Threads
     python3 Main.py
     ```

4. **Connect the phone’s MQTT client**.

5. **Run the laptop `Main.py` (RelayClient integrated with internal communications)**.
