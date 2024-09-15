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

relay_server = RelayServer(host = relayhost,port = relayport,IMU_queue=IMU_queue, game_engine_queue=game_engine_queue)
ai = AI(IMU_queue=IMU_queue,action_queue=action_queue)
game_engine = GameEngine(action_queue=action_queue, game_engine_queue = game_engine_queue,viz_queue=viz_queue, eval_queue=eval_queue)
eval_client = EvalClient(eval_queue=eval_queue,server_ip=evalhost,server_port=evalport)
visualizer = MQTT(viz_queue=viz_queue)

threads = [relay_server, ai, game_engine, eval_client, visualizer]
try:
    relay_server.start()
    print("starting relay server thread")
    ai.start()
    print("starting AI thread ")
    game_engine.start()
    print("starting game engine thread")
    eval_client.start()
    print("start eval client thread")
    visualizer.start()
    print("start visualizer thread")
    print("_"*30)
    print()
    
    relay_server.join()
    ai.join()
    game_engine.join()
    eval_client.join()
    visualizer.join()

except KeyboardInterrupt:
    print("\nShutting down..")
    relay_server.shutdown()
    visualizer.shutdown()


