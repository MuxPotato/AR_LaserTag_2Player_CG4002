import json
import re

def processMessage(msg):
    try:
        print(f"Original message: {msg}")  # Debug: Print the raw message

        # Use regex to capture packet type and packet data
        match = re.match(r"'?(\w+)'?:\s*(\{.*\})", msg)
        if not match:
            raise ValueError("Message format is incorrect")

        packet_type = match.group(1)  # Extract packet type
        packet_data_str = match.group(2)  # Extract packet data string

        print(f"Packet type: {packet_type}")
        print(f"Packet data string: {packet_data_str}")

        # Convert the packet data string to a dictionary using json.loads
        # First, replace single quotes with double quotes in packet_data_str
        packet_data_str = re.sub(r"(?<!\\)'", '"', packet_data_str)


        packet_data_str = packet_data_str.replace("False", "false").replace("True", "true").replace("None", "null")
        print(f"full packet : {packet_type} + {packet_data_str}")

        # Now, parse the string as JSON
        packet_data = json.loads(packet_data_str)

        # Process based on packet type
        if packet_type == 'IMUPacket' and 'accel' in packet_data and 'gyro' in packet_data:
            print(f"Processing IMUPacket: {packet_data}")
            # self.IMU_queue.put(packet_data)

        elif packet_type == 'ShootPacket' and 'isFired' in packet_data:
            print(f"Send to AI: {packet_data}")
            # self.fire_queue.put(packet_data['isFired'])

        elif packet_type == 'ShootPacket' and 'isHit' in packet_data:
            print(f"Send to game engine: {packet_data}")
            # self.shot_queue.put(packet_data['isHit'])

        else:
            print("Unknown packet type received")

    except json.JSONDecodeError as e:
        print(f"Error processing message: Invalid JSON -> {e}")
    except ValueError as e:
        print(f"Error processing message: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")


def simulateClientWithLogFile(log_file_path):
    """Simulate receiving data from a client by reading from a log file."""
    try:
        with open(log_file_path, 'r') as log_file:
            for line in log_file:
                line = line.strip()
                if line:
                    processMessage(line)
                # time.sleep(0.1)  # Simulate 10 packets per second
    except Exception as e:
        print(f"Error reading log file: {e}")


def main():
    simulateClientWithLogFile('packets_from_beetles.log')


if __name__ == "__main__":
    main()

