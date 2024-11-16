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





relayhost = '172.26.191.210'

#socket.gethostbyname(socket.gethostname())
relayport = 5055

#evalhost = '127.0.0.1'
#evalport = 9999

#evalport = 41363


P1_IMU_queue = queue.Queue()
P2_IMU_queue = queue.Queue()
viz_queue = queue.Queue()

P1_action_queue = queue.Queue()
P2_action_queue = queue.Queue()

phone1_response_queue = queue.Queue()
phone2_response_queue = queue.Queue()
to_rs_queue = queue.Queue()
shot_queue = queue.Queue()
P1_fire_queue = queue.Queue()
P2_fire_queue = queue.Queue()
P1_ankle_queue = queue.Queue()
P2_ankle_queue = queue.Queue()

# OLD
# relay_server = RelayServer(host = relayhost,port = relayport,P1_IMU_queue=P1_IMU_queue,P2_IMU_queue=P2_IMU_queue,shot_queue = shot_queue,P1_fire_queue = P1_fire_queue,P2_fire_queue = P2_fire_queue,P1_ankle_queue = P1_ankle_queue,P2_ankle_queue = P2_ankle_queue,to_rs_queue = to_rs_queue)
# p1_ai = AIOne(P1_IMU_queue=P1_IMU_queue,action_queue=P1_action_queue, P1_fire_queue = P1_fire_queue,P1_ankle_queue = P1_ankle_queue)
# p2_ai = AITwo(P2_IMU_queue=P2_IMU_queue,action_queue=P2_action_queue, P2_fire_queue = P2_fire_queue,P2_ankle_queue = P2_ankle_queue)
# game_engine = GameEngine(P1_action_queue=P1_action_queue,P2_action_queue=P2_action_queue,viz_queue=viz_queue, phone_response_queue=phone_response_queue,shot_queue = shot_queue,to_rs_queue = to_rs_queue)
# visualizer_mqtt = MQTT(viz_queue=viz_queue,phone_response_queue=phone_response_queue)



# NEW
relay_server = RelayServer(host = relayhost,port = relayport,P1_IMU_queue=P1_IMU_queue,P2_IMU_queue=P2_IMU_queue,shot_queue = shot_queue,P1_fire_queue = P1_fire_queue,P2_fire_queue = P2_fire_queue,P1_ankle_queue = P1_ankle_queue,P2_ankle_queue = P2_ankle_queue,to_rs_queue = to_rs_queue)
p1_ai = AIOne(P1_IMU_queue=P1_IMU_queue,P1_action_queue=P1_action_queue, P1_fire_queue = P1_fire_queue,P1_ankle_queue = P1_ankle_queue, viz_queue=viz_queue)
p2_ai = AITwo(P2_IMU_queue=P2_IMU_queue,P2_action_queue=P2_action_queue, P2_fire_queue = P2_fire_queue,P2_ankle_queue = P2_ankle_queue, viz_queue=viz_queue)
game_engine = GameEngine(P1_action_queue=P1_action_queue,P2_action_queue=P2_action_queue,viz_queue=viz_queue, phone1_response_queue=phone1_response_queue,phone2_response_queue=phone2_response_queue,shot_queue = shot_queue,to_rs_queue = to_rs_queue)
visualizer_mqtt = MQTT(viz_queue=viz_queue,phone1_response_queue=phone1_response_queue,phone2_response_queue=phone2_response_queue)



threads = [relay_server, p1_ai, p2_ai,game_engine, visualizer_mqtt]
try:
    relay_server.start()
    print("starting relay server thread")
    p1_ai.start()
    print("starting player 1 AI thread")
    p2_ai.start()
    print("starting player 2 AI thread")
    game_engine.start()
    print("starting game engine thread")
    visualizer_mqtt.start()
    print("starting visualizer_mqtt thread")
    print("_"*30)

    
    
    relay_server.join()
    p1_ai.join()
    p2_ai.join()
    game_engine.join()
    visualizer_mqtt.join()

except KeyboardInterrupt:
    print("\nShutting down..")
    relay_server.shutdown()
    visualizer_mqtt.shutdown()


