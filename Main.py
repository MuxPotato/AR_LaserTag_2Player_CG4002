import threading 
import queue 
import time
import socket 
from EvalClient import EvalClient
from MQTT import MQTT
from RelayServer import RelayServer
from GameEngine import GameEngine
from AIThread import AI 


#host = '172.26.190.191'
relayhost = '172.26.190.191'
#socket.gethostbyname(socket.gethostname())
relayport = 5055

evalhost = '127.0.0.1'
evalport = 8888

IMU_queue = queue.Queue()
action_queue = queue.Queue()
game_engine_queue = queue.Queue()
viz_queue = queue.Queue()
eval_queue = queue.Queue()
phone_action_queue = queue.Queue() # Added

relay_server = RelayServer(host = relayhost,port = relayport,IMU_queue=IMU_queue, game_engine_queue=game_engine_queue)
ai = AI(IMU_queue=IMU_queue,action_queue=action_queue)
#game_engine = GameEngine(action_queue=action_queue, game_engine_queue = game_engine_queue,viz_queue=viz_queue, eval_queue=eval_queue)
game_engine = GameEngine(action_queue=action_queue, game_engine_queue = game_engine_queue,viz_queue=viz_queue, eval_queue=eval_queue,phone_action_queue=phone_action_queue)
eval_client = EvalClient(eval_queue=eval_queue,server_ip=evalhost,server_port=evalport)
visualizer = MQTT(viz_queue=viz_queue,phone_action_queue=phone_action_queue)

threads = [relay_server, ai, game_engine, eval_client, visualizer]
try:
    relay_server.start()
    print("starting relay server thread")
    ai.start()
    print("starting AI thread")
    game_engine.start()
    print("starting game engine thread")
    eval_client.start()
    print("starting eval client thread")
    visualizer.start()
    print("starting visualizer thread")
    print("_"*30)

    ## ADDED
    # Simulate user input to send actions to GameEngine
    while True:
        action_input = input("Enter a move (e.g., 'shoot:1', 'reload:2', 'basket:1'): ").strip()
        if action_input in ["exit", "quit"]:
            print("Exiting the system...")
            break  # Exit the input loop
        if ":" in action_input:
            # Simulate sending the action to the phone_action_queue of GameEngine
            phone_action_queue.put(action_input)
            print(f"Action '{action_input}' sent to GameEngine.")
        else:
            print("Invalid input format. Please use the format 'action:player_id'.")

    # After breaking out of the loop, you can cleanly shut down threads
    relay_server.shutdown()  # Signal the relay server to shut down
    visualizer.shutdown()    # Signal the visualizer (MQTT) to shut down
    
    
    relay_server.join()
    ai.join()
    game_engine.join()
    eval_client.join()
    visualizer.join()

except KeyboardInterrupt:
    print("\nShutting down..")
    relay_server.shutdown()
    visualizer.shutdown()


