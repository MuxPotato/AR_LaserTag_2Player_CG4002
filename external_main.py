import sys 
import queue
import time
import traceback

from external_utils import dump_to_file, read_user_input
from internal_main import InternalMainThread
from internal_utils import bcolors
from relay_client import RelayClient

# Constants
SERVER_IP = "172.26.191.210"
SERVER_PORT = 5055

if __name__=="__main__":
    outgoing_glove_queue = queue.Queue()
    outgoing_game_state_queue = queue.Queue()
    incoming_game_state_queue = queue.Queue()
    int_main = InternalMainThread(outgoing_glove_queue,outgoing_game_state_queue,incoming_game_state_queue)
#    output_dir = "output/"
    glove_output_filename = read_user_input("Enter the filename to dump glove data to: ")
    game_state_output_filename = read_user_input("Enter the filename to dump game state data to: ")
    relay_client = RelayClient(SERVER_IP, SERVER_PORT, outgoing_glove_queue, outgoing_game_state_queue, incoming_game_state_queue)
    # TODO: Remove 2 lines below
#    relay_client = RelayClient(outgoing_glove_queue, outgoing_game_state_queue,
#            f"""{output_dir}/{glove_output_filename}""", f"""{output_dir}/{game_state_output_filename}""")
    try:
        int_main.start()
        relay_client.start()
        int_main.join()
        relay_client.join()
    except KeyboardInterrupt:
        print(f"""{bcolors.BRIGHT_RED}Stopping...{bcolors.ENDC}""")
        int_main.quit()
        relay_client.quit()
        time.sleep(1)
        print(f"""Number of elements in outgoing glove queue: {outgoing_glove_queue.qsize()}""")
        print(f"""Number of elements in outgoing game state queue: {outgoing_game_state_queue.qsize()}""")
    except Exception as exc:
        traceback.print_exception(exc)
    sys.exit(0)
