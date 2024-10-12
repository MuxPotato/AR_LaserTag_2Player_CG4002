COLOR_CODES = {
    'Relay Server': '\033[31m',  # Red
    'AI Thread': '\033[32m',     # Green
    'Eval Client': '\033[33m',   # Yellow
    'Game Engine': '\033[34m',   # Blue
    'MQTT': '\033[35m'           # Magenta
}


RESET_COLOR = '\033[0m'

def print_message(category,message):
    color = COLOR_CODES.get(category,'\033[30m')
    print(f"{color}[{category}]{message}{RESET_COLOR}")