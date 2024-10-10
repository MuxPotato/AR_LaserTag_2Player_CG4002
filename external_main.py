import sys 
import queue
import time
import traceback

from external_utils import PlayerData, dump_to_file
from internal_main import InternalMainThread

if __name__=="__main__":
    outgoing_glove_queue = queue.Queue()
    outgoing_game_state_queue = queue.Queue()
    incoming_game_state_queue = queue.Queue()
    int_main = InternalMainThread(outgoing_glove_queue,outgoing_game_state_queue,incoming_game_state_queue)
    try:
        int_main.start()
        int_main.join()
    except KeyboardInterrupt:
        int_main.quit()
        """ print("Outgoing glove queue: ",outgoing_glove_queue)
        print("Outgoing game state queue: ",outgoing_game_state_queue)
        print("Incoming game state queue: ",incoming_game_state_queue) """
        time.sleep(1)
        dump_to_file(outgoing_glove_queue, "glove")
        dump_to_file(outgoing_game_state_queue, "outgoing game state")
        dump_to_file(incoming_game_state_queue, "incoming game state")
    except Exception as exc:
        traceback.print_exception(exc)
    sys.exit(0)
