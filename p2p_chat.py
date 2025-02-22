import socket
import threading
import json
import os

peer_list = []
active_peers = set()
peer_list_lock = threading.Lock()
active_peers_lock = threading.Lock()
PEER_FILE = "peers.json"

def load_peers():
    global peer_list
    if os.path.exists(PEER_FILE):
        with open(PEER_FILE, "r") as f:
            try:
                data = json.load(f)
                if isinstance(data, list):
                    peer_list = []
                    for item in data:
                        if isinstance(item, dict):
                            peer_list.append(item)
                        else:
                            if isinstance(item, (list, tuple)) and len(item) == 2:
                                peer_list.append({"ip": item[0], "port": item[1], "status": "inactive"})
            except json.JSONDecodeError:
                peer_list = []
    else:
        peer_list = []

def save_peers():
    with peer_list_lock:
        with open(PEER_FILE, "w") as f:
            json.dump(peer_list, f)

def start_server(my_ip, my_port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((my_ip, my_port))
    server.listen(5)
    print(f"🚀 [SERVER STARTED] Listening on {my_ip}:{my_port}")

    while True:
        client_socket, addr = server.accept()
        threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()

def handle_client(client_socket):
    try:
        message = client_socket.recv(1024).decode().strip()
        if message:
            parts = message.split(" ", 2)
            if len(parts) == 3:
                sender_info, team_name, msg = parts
                sender_ip, sender_port = sender_info.split(":")
                sender_port = int(sender_port)

                if msg.lower() == "exit":
                    with active_peers_lock:
                        active_peers.discard((sender_ip, sender_port))
                    update_peer_status(sender_ip, sender_port, "inactive")
                    print(f"❌ Peer {sender_ip}:{sender_port} has disconnected.")
                else:
                    with active_peers_lock:
                        active_peers.add((sender_ip, sender_port))
                    update_peer_status(sender_ip, sender_port, "active")
                    print(f"📩 [MESSAGE RECEIVED] From {team_name} ({sender_ip}:{sender_port}): {msg}")
    except Exception as e:
        print(f"❌ Error handling client message: {e}")
    finally:
        client_socket.close()

def update_peer_status(ip, port, status):
    with peer_list_lock:
        for peer in peer_list:
            if peer["ip"] == ip and peer["port"] == port:
                peer["status"] = status
                return
        peer_list.append({"ip": ip, "port": port, "status": status})

def send_message(target_ip, target_port, my_ip, my_port, team_name, msg):
    if target_ip == my_ip and target_port == my_port:
        print("❌ [ERROR] Cannot send a message to yourself.")
        return

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    try:
        print(f"🔗 Attempting to connect to {target_ip}:{target_port}...")
        client.connect((target_ip, target_port))
        formatted_msg = f"{my_ip}:{my_port} {team_name} {msg}"
        client.sendall(formatted_msg.encode())
        print(f"✅ [MESSAGE SENT] To {target_ip}:{target_port}: {msg}")

        with active_peers_lock:
            active_peers.add((target_ip, target_port))
        update_peer_status(target_ip, target_port, "active")
    except socket.timeout:
        print(f"❌ [TIMEOUT] Could not connect to {target_ip}:{target_port} within 5 seconds.")
    except ConnectionRefusedError:
        print(f"❌ [CONNECTION REFUSED] The peer {target_ip}:{target_port} is not accepting connections.")
    except Exception as e:
        print(f"❌ [FAILED] Could not send to {target_ip}:{target_port}: {e}")
    finally:
        client.close()

def send_message_in_thread(target_ip, target_port, my_ip, my_port, team_name, msg):
    threading.Thread(
        target=send_message,
        args=(target_ip, target_port, my_ip, my_port, team_name, msg),
        daemon=True
    ).start()

def query_active_peers():
    with active_peers_lock:
        if active_peers:
            print("\n🌍 [ACTIVE PEERS LIST]")
            for peer in active_peers:
                print(f"   {peer[0]}:{peer[1]}")
        else:
            print("\n❌ [NO ACTIVE PEERS FOUND]")

def query_peer_list(my_ip, my_port):
    with peer_list_lock:
        if peer_list:
            print("\n🌍 [ALL KNOWN PEERS LIST]")
            for peer in peer_list:
                if peer["ip"] != my_ip or peer["port"] != my_port:
                    status = peer.get("status", "unknown")
                    print(f"   {peer['ip']}:{peer['port']} - {status}")
        else:
            print("\n❌ [NO KNOWN PEERS FOUND]")

def send_message_to_all(my_ip, my_port, team_name, msg):
    with peer_list_lock:
        for peer in peer_list:
            target_ip, target_port = peer["ip"], peer["port"]
            if (target_ip, target_port) != (my_ip, my_port):
                send_message_in_thread(target_ip, target_port, my_ip, my_port, team_name, msg)

def connect_to_peer(my_ip, my_port, team_name):
    query_active_peers()
    try:
        target_ip = input("📩 Enter the IP address of the peer to connect to: ").strip()
        target_port = int(input("📩 Enter the port number of the peer to connect to: ").strip())
        send_message_in_thread(target_ip, target_port, my_ip, my_port, team_name, "Hello, peer!")
    except ValueError:
        print("❌ [ERROR] Invalid port number. Please enter a valid integer.")

def send_exit_message(my_ip, my_port, team_name):
    with active_peers_lock:
        for peer in active_peers.copy():
            target_ip, target_port = peer
            send_message_in_thread(target_ip, target_port, my_ip, my_port, team_name, "exit")

def main():
    load_peers()
    my_ip = "10.15.5.25"
    team_name = input("🔹 Enter your team name (default: TheBlocksmiths): ").strip()
    if not team_name:
        team_name = "TheBlocksmiths"
    my_port = int(input("🔹 Enter your port number: ").strip())

    # Send messages to mandatory peers at startup
    mandatory_peers = [("10.206.4.122", 1255), ("10.206.5.228", 6555)]
    for ip, port in mandatory_peers:
        if (ip, port) != (my_ip, my_port):
            send_message_in_thread(ip, port, my_ip, my_port, team_name, "Hello, mandatory peer!")

    # Start the server in a separate thread
    threading.Thread(target=start_server, args=(my_ip, my_port), daemon=True).start()

    while True:
        print("\n***** 🛠 [MAIN MENU] *****")
        print("1. Send a Message")
        print("2. Query Active Peers")
        print("3. Send Message to All Peers")
        print("4. Query Known Peers")
        print("5. Connect to a Peer")
        print("0. Quit")
        choice = input("🔹 Enter choice: ").strip()

        if choice == "1":
            target_ip = input("📩 Enter recipient's IP address: ").strip()
            target_port = int(input("📩 Enter recipient's port number: ").strip())
            msg = input("💬 Enter your message: ").strip()
            send_message_in_thread(target_ip, target_port, my_ip, my_port, team_name, msg)
        elif choice == "2":
            query_active_peers()
        elif choice == "3":
            msg = input("💬 Enter your message: ").strip()
            send_message_to_all(my_ip, my_port, team_name, msg)
        elif choice == "4":
            query_peer_list(my_ip, my_port)
        elif choice == "5":
            connect_to_peer(my_ip, my_port, team_name)
        elif choice == "0":
            send_exit_message(my_ip, my_port, team_name)
            save_peers()
            print("👋 [EXITING] Goodbye!")
            break
        else:
            print("❌ Invalid choice. Try again.")

if __name__ == "__main__":
    main()
    
