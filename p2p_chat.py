import socket
import threading

peer_list = set() 
peer_list_lock = threading.Lock() 

def start_server(my_ip, my_port):
    """Starts the server to receive messages from peers."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((my_ip, my_port))
    server.listen(5)
    print(f"\n🚀 [SERVER STARTED] Listening on {my_ip}:{my_port}\n{'-'*50}")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

def handle_client(client_socket):
    """Handles incoming messages from a peer."""
    try:
        message = client_socket.recv(1024).decode().strip()
        if message:
            parts = message.split(" ", 2)
            if len(parts) == 3:
                sender_info, team_name, msg = parts
                sender_ip, sender_port = sender_info.split(":")
                sender_port = int(sender_port)

                with peer_list_lock:
                    peer_list.add((sender_ip, sender_port))

                print(f"\n📩 [MESSAGE RECEIVED] From {team_name} ({sender_ip}:{sender_port})")
                print(f"   ➤ {msg}\n{'-'*50}")
            else:
                print(f"\n⚠️ [MALFORMED MESSAGE] {message}\n{'-'*50}")
    except Exception as e:
        print(f"❌ Error handling client message: {e}")
    finally:
        client_socket.close()

def send_message(target_ip, target_port, my_ip, my_port, team_name, msg):
    """Sends a message to a target peer."""
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((target_ip, target_port))

        # Standardized message format: "<IP:PORT> <team name> <message>"
        formatted_msg = f"{my_ip}:{my_port} {team_name} {msg}"
        client.send(formatted_msg.encode())

        print(f"\n✅ [MESSAGE SENT] To {target_ip}:{target_port}")
        print(f"   ➤ {msg}\n{'-'*50}")
    except Exception as e:
        print(f"❌ [FAILED] Could not send to {target_ip}:{target_port} → {e}\n{'-'*50}")
    finally:
        client.close()

def query_peers():
    """Displays known peers in a structured format."""
    with peer_list_lock:
        if peer_list:
            print("\n🌍 [CONNECTED PEERS LIST]\n" + "-"*50)
            for index, peer in enumerate(peer_list, 1):
                print(f"   {index}. {peer[0]}:{peer[1]}")
            print("-"*50)
        else:
            print("\n❌ [NO CONNECTED PEERS FOUND]\n" + "-"*50)

def connect_to_peers(team_name, my_ip, my_port):
    """Attempts to connect to known peers."""
    with peer_list_lock:
        if not peer_list:
            print("\n❌ [NO PEERS TO CONNECT TO]\n" + "-"*50)
            return

        print("\n🔗 [CONNECTING TO PEERS]\n" + "-"*50)
        for peer_ip, peer_port in peer_list:
            print(f"   🔗 Connecting to {peer_ip}:{peer_port}...")
            send_message(peer_ip, peer_port, my_ip, my_port, team_name, "Hello, peer! Connecting...")

def main():
    my_ip = input("🔹 Enter your IP address (Use 0.0.0.0 to listen on all interfaces): ").strip()
    my_port = int(input("🔹 Enter your fixed port: ").strip())
    team_name = input("🔹 Enter your team name: ").strip()

    threading.Thread(target=start_server, args=(my_ip, my_port), daemon=True).start()

    while True:
        print("\n***** 🛠 [MAIN MENU] *****")
        print("1️⃣ Send a Message")
        print("2️⃣ View Connected Peers")
        print("3️⃣ Connect to Peers")
        print("0️⃣ Quit")
        print("-" * 50)

        choice = input("🔹 Enter choice: ").strip()

        if choice == "1":
            target_ip = input("📩 Enter recipient's IP address: ").strip()
            target_port = int(input("📩 Enter recipient's port number: ").strip())
            msg = input("💬 Enter your message: ").strip()
            send_message(target_ip, target_port, my_ip, my_port, team_name, msg)

        elif choice == "2":
            query_peers()

        elif choice == "3":
            connect_to_peers(team_name, my_ip, my_port)

        elif choice == "0":
            print("\n👋 [EXITING] Goodbye!\n" + "-"*50)
            break

if __name__ == "__main__":
    main()
