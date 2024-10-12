import ast 

def processMessage(msg):
    # Check and parse the message
    try:
        # Split the packet type from the dictionary portion
        if ": {" in msg:
            packet_type, packet_data = msg.split(": ", 1)
            packet_type = packet_type.strip("'")  # Remove surrounding quotes from the packet type

            # Convert the remaining string to a Python dictionary
            packet_data = eval(packet_data)  # Safe here since we're controlling the input

            # Process based on packet type
            if packet_type == 'IMUPacket' and 'accel' in packet_data and 'gyro' in packet_data:
                print(packet_data)
                # Add to IMU queue here if needed, e.g., self.IMU_queue.put(packet_data)
            
            elif packet_type == 'ShootPacket' and ('isFired' in packet_data or 'isHit' in packet_data):
                print(packet_data)
                # Add to shoot queue here if needed, e.g., self.shoot_queue.put(packet_data)
            
            else:
                print("Unknown packet type received")
        else:
            print("Invalid message format")

    except SyntaxError as e:
        print(f"Syntax error in message: {msg} -> {e}")
    except KeyError as e:
        print(f"Missing key in message: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")
def simulateClientWithLogFile(log_file_path):
        """Simulate receiving data from a client by reading from a log file."""
        try:
            with open(log_file_path, 'r') as log_file:
                for line in log_file:
                    line  = line.strip()
                    if line: 
                        processMessage(line)
                    #time.sleep(0.1)  # Simulate 10 packets per second
        except Exception as e:
            print(f"Error reading log file: {e}")
    
def main():
    simulateClientWithLogFile('packets_from_beetles.log')

if __name__ == "__main__":
    main()