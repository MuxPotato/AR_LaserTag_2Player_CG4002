
## RelayServer.py
Receives data from gun, vest, ankle, and glove beetles through RelayClient. Sends the data to both AI threads through respective P1 and P2 IMU queues. Also sends whether the player is shot to the game engine thread. Sends hp and bullets back to RelayClient to update beetles.

## AIOne.py
Predicts action for player 1 and sends `action:player_id` through `P1_action_queue` to the game engine. Sends field of view query to MQTT client through `viz_queue`.

## AITwo.py
Predicts action for player 2 and sends `action:player_id` through `P2_action_queue` to the game engine. Sends field of view query to MQTT client through `viz_queue`.

## GameEngine.py
Receives action from AI. Receives field of view from phone through MQTT. Calculates game state. Sends it to the eval client through the `eval_queue`. Receives updated game state. Updates phones through MQTT and beetles through RelayServer thread.

## MQTT.py
Gets data from `viz_queue` and publishes it in the `gamestate` topic. Receives response (hit or miss information) from the phone in the `response` topic. Sends response back to the game engine through the respective player response queue.

## EvalClient.py
Sends the eval server the encrypted JSON game state. Receives the correct game state from the eval server and sends it to the game engine through `from_eval_queue`.

# Setup

1. **Run the eval server first**:
   - Go to `eval_server/server`.
   - Run `bash run_server.sh`.
   - Open the `html` folder and open the 1-player HTML page.
   - Enter `127.0.0.1`, `BO3`, and `PLEASEMAYITWORKS` as the password.
   - Log in and set up reverse tunneling:
     ```bash
     ssh -R 9999:localhost:64195 xilinx@makerslab-fpga-25.d2.comp.nus.edu.sg
     ```
   - Use the port displayed on the HTML page.

2. **Run the MQTT broker**:
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
