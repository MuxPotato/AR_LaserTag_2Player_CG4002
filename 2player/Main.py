import threading 
import queue 
import time
import socket 
from EvalClient import EvalClient
from MQTT import MQTT
from RelayServer import RelayServer
from GameEngine import GameEngine
from AIOne import AIOne
from AITwo import AITwo


#host = '172.26.190.191'
relayhost = '172.26.191.210'
#socket.gethostbyname(socket.gethostname())
P1_IMU_PORT = 5055
P2_IMU_PORT = 5056
SHOOT_VEST_PORT = 5057

evalhost = '127.0.0.1'
EVALPORT = 8888


P1_IMU_queue = queue.Queue()
P2_IMU_queue = queue.Queue()
#game_engine_queue = queue.Queue()
viz_queue = queue.Queue()
eval_queue = queue.Queue()
phone_action_queue = queue.Queue() # Added
from_eval_queue = queue.Queue()
phone_response_queue = queue.Queue()
to_rs_queue = queue.Queue()
shot_queue = queue.Queue()
P1_fire_queue = queue.Queue()
P2_fire_queue = queue.Queue()


relay_server = RelayServer(host = relayhost,P1_imu_port = P1_IMU_PORT,P2_imu_port = P2_IMU_PORT,shoot_vest_port = SHOOT_VEST_PORT,P1_IMU_queue=P1_IMU_queue,P2_IMU_queue=P2_IMU_queue,shot_queue = shot_queue,fire_queue = fire_queue,to_rs_queue = to_rs_queue)
p1_ai = AIOne(P1_IMU_queue=P1_IMU_queue,phone_action_queue=phone_action_queue, P1_fire_queue = P1_fire_queue)
p2_ai = AITwo(P2_IMU_queue=P2_IMU_queue,phone_action_queue=phone_action_queue, P2_fire_queue = P2_fire_queue)
game_engine = GameEngine(phone_action_queue=phone_action_queue,viz_queue=viz_queue, eval_queue=eval_queue, from_eval_queue = from_eval_queue, phone_response_queue=phone_response_queue,shot_queue = shot_queue,to_rs_queue = to_rs_queue)
eval_client = EvalClient(eval_queue=eval_queue,server_ip=evalhost,server_port=EVALPORT,from_eval_queue = from_eval_queue)
visualizer_mqtt = MQTT(viz_queue=viz_queue,phone_action_queue=phone_action_queue,phone_response_queue=phone_response_queue)

threads = [relay_server, p1_ai, p2_ai,game_engine, eval_client, visualizer_mqtt]
try:
    relay_server.start()
    print("starting relay server thread")
    p1_ai.start()
    print("starting player 1 AI thread")
    p2_ai.start()
    print("starting player 2 AI thread")
    game_engine.start()
    print("starting game engine thread")
    eval_client.start()
    print("starting eval client thread")
    visualizer_mqtt.start()
    print("starting visualizer_mqtt thread")
    print("_"*30)

    
    
    relay_server.join()
    p1_ai.join()
    p2_ai.join()
    game_engine.join()
    eval_client.join()
    visualizer_mqtt.join()

except KeyboardInterrupt:
    print("\nShutting down..")
    relay_server.shutdown()
    visualizer_mqtt.shutdown()


