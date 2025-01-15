import socket
import struct
import threading
import time
import sys

MAGIC_COOKIE = 0xabcddcba
MESSAGE_TYPE_OFFER = 0x2
MESSAGE_TYPE_REQUEST = 0x3
MESSAGE_TYPE_PAYLOAD = 0x4

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class Server:
    def __init__(self, tcp_port=11111, udp_port=54545):
        self.TCP_PORT = tcp_port
        self.UDP_PORT = udp_port
        self.udp_socket = None
        self.tcp_socket = None

    def build_payload_packet(self, total_segments: int, current_segment: int, payload_size: int = 1024) -> bytes:
        """
        Build the 'payload' packet (server to client).
        """
        header = struct.pack("!IbQQ", MAGIC_COOKIE, MESSAGE_TYPE_PAYLOAD, total_segments, current_segment)
        payload_data = b"a" * payload_size
        return header + payload_data

    def tcp_client(self, client_socket: socket.socket, client_address: tuple):
        """
        Handle a single TCP client connection.
        Receives the requested file size and sends back the data.
        """
        try:
            print(f"{Colors.OKBLUE}TCP Connected to {client_address}{Colors.ENDC}")
            data = b""
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break
            file_size_str = data.strip().decode()
            file_size = int(file_size_str)
            print(f"{Colors.OKCYAN}TCP Client {client_address} requested {file_size} bytes{Colors.ENDC}")

            bytes_sent = 0
            chunk_data = b"a" * 4096

            start_time = time.time()

            while bytes_sent < file_size:
                send_size = min(4096, file_size - bytes_sent)
                client_socket.sendall(chunk_data[:send_size])
                bytes_sent += send_size

            duration = time.time() - start_time
            speed = (bytes_sent * 8) / duration
            print(f"{Colors.OKGREEN}TCP Sent {bytes_sent} bytes to {client_address} in {duration:.2f}s at {speed:.2f} bits/sec{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}TCP Error with client {client_address}: {e}{Colors.ENDC}")
        finally:
            client_socket.close()
            print(f"{Colors.WARNING}TCP Connection to {client_address} closed{Colors.ENDC}")

    def udp_client(self, udp_socket: socket.socket, client_address: tuple, file_size: int):
        """
        Handle a single UDP client request.
        Sends back the requested data in segments.
        """
        try:
            print(f"{Colors.OKBLUE}UDP Handling request from {client_address} for {file_size} bytes{Colors.ENDC}")
            total_segments = (file_size + 1023) // 1024
            start_time = time.time()

            for segment in range(1, total_segments + 1):
                payload_packet = self.build_payload_packet(total_segments, segment)
                udp_socket.sendto(payload_packet, client_address)

            duration = time.time() - start_time
            speed = (file_size * 8) / duration
            print(f"{Colors.OKGREEN}UDP Sent {total_segments} segments to {client_address} in {duration:.2f}s at {speed:.2f} bits/sec{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}UDP Error with client {client_address}: {e}{Colors.ENDC}")

    def udp_requests(self, udp_socket: socket.socket):
        """
        Continuously listen for UDP client requests and handle them in separate threads.
        """
        while True:
            try:
                data, client_address = udp_socket.recvfrom(1024)
                print(f"{Colors.OKCYAN}UDP Received data from {client_address}{Colors.ENDC}")
                if len(data) < 13:
                    print(f"{Colors.WARNING}UDP Invalid packet size from {client_address}{Colors.ENDC}")
                    continue

                magic_cookie, message_type, file_size = struct.unpack("!IBQ", data[:13])
                if magic_cookie != MAGIC_COOKIE or message_type != MESSAGE_TYPE_REQUEST:
                    print(f"{Colors.WARNING}UDP Invalid request format from {client_address}{Colors.ENDC}")
                    continue

                print(f"{Colors.OKGREEN}UDP Valid request from {client_address} for {file_size} bytes{Colors.ENDC}")

                threading.Thread(target=self.udp_client, args=(udp_socket, client_address, file_size), daemon=True).start()
            except Exception as e:
                print(f"{Colors.FAIL}UDP Error receiving data: {e}{Colors.ENDC}")

    def start_server(self):
        """
        Main function to start the server.
        """
        try:
            hostname = socket.gethostname()
            server_ip = socket.gethostbyname(hostname)
            print(f"{Colors.HEADER}Server started, listening on IP address {server_ip}{Colors.ENDC}")
            print(f"{Colors.HEADER}UDP Port: {self.UDP_PORT}, TCP Port: {self.TCP_PORT}{Colors.ENDC}")

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.bind(('', self.UDP_PORT))
            threading.Thread(target=self.udp_requests, args=(self.udp_socket,), daemon=True).start()

            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('', self.TCP_PORT))
            self.tcp_socket.listen(5)
            print(f"{Colors.OKBLUE}TCP server listening on port {self.TCP_PORT}{Colors.ENDC}")

            while True:
                client_socket, client_address = self.tcp_socket.accept()
                threading.Thread(target=self.tcp_client, args=(client_socket, client_address), daemon=True).start()

        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}Server shutting down...{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}Server error: {e}{Colors.ENDC}")
        finally:
            sys.exit(0)

if __name__ == "__main__":
    server = Server()
    server.start_server()
