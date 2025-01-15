import socket
import struct
import threading
import time
import sys

MAGIC_COOKIE = 0xabcddcba
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


class Client:
    def __init__(self, server_ip, udp_port, tcp_port, file_size, num_tcp, num_udp):
        self.server_ip = server_ip
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.file_size = file_size
        self.num_tcp = num_tcp
        self.num_udp = num_udp

    def create_message(self):
        byte = b"a"
        message = byte*self.file_size + b"\n"
        return message

    def tcp_transfer(self, transfer_id):
        """
        Perform a TCP file transfer to the server and measure speed.
        """
        try:
            start_time = time.time()
            with socket.create_connection((self.server_ip, self.tcp_port)) as tcp_socket:
                file = self.create_message()
                tcp_socket.sendall(file.encode())
                received_data = 0
                while received_data < self.file_size:
                    data = tcp_socket.recv(4096)
                    if not data:
                        break
                    received_data += len(data)
            duration = time.time() - start_time
            speed = (self.file_size * 8) / duration
            print(f"{Colors.OKGREEN}TCP Transfer #{transfer_id} finished, total time: {duration:.3f}s, speed: {speed:.3f} bits/sec{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}TCP Transfer #{transfer_id} error: {e}{Colors.ENDC}")

    def udp_transfer(self, transfer_id):
        """
        Perform a UDP file transfer to the server and measure speed and packet loss.
        """
        try:
            udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_socket.settimeout(1)
            request_packet = struct.pack("!IBQ", MAGIC_COOKIE, MESSAGE_TYPE_REQUEST, self.file_size)
            udp_socket.sendto(request_packet, (self.server_ip, self.udp_port))
            print(f"{Colors.OKGREEN}UDP Sent request to {self.server_ip}:{self.udp_port} for {self.file_size} bytes{Colors.ENDC}")

            received_segments = set()
            total_segments = (self.file_size + 1023) // 1024
            start_time = time.time()

            while True:
                try:
                    data, _ = udp_socket.recvfrom(2048)
                    if len(data) < 21:
                        print(f"{Colors.WARNING}UDP Received invalid payload size{Colors.ENDC}")
                        continue
                    magic_cookie, message_type, total_segments_recv, segment_number = struct.unpack("!IBQQ", data[:21])
                    if magic_cookie == MAGIC_COOKIE and message_type == MESSAGE_TYPE_PAYLOAD:
                        received_segments.add(segment_number)
                        print(f"{Colors.OKGREEN}UDP Received segment {segment_number}/{total_segments_recv}{Colors.ENDC}")
                except socket.timeout:
                    print(f"{Colors.WARNING}UDP UDP receive timed out{Colors.ENDC}")
                    break

            duration = time.time() - start_time
            bytes_received = len(received_segments) * 1024
            speed = (bytes_received * 8) / duration if duration > 0 else 0  # bits per second
            packet_loss = 100 - (len(received_segments) / total_segments * 100) if total_segments > 0 else 0
            print(f"{Colors.OKGREEN}[UDP] Transfer #{transfer_id} finished, total time: {duration:.2f}s, speed: {speed:.2f} bits/sec, packet loss: {packet_loss:.2f}%{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}[UDP] Transfer #{transfer_id} error: {e}{Colors.ENDC}")
        finally:
            udp_socket.close()

    def start_transfers(self):
        """
        Starts the TCP and UDP transfers concurrently using threads.
        """
        threads = []
        counter = 1

        # TCP
        for i in range(1, self.num_tcp + 1):
            t = threading.Thread(target=self.tcp_transfer, args=(counter,), daemon=True)
            threads.append(t)
            counter += 1
            t.start()

        # UDP
        for i in range(1, self.num_udp + 1):
            t = threading.Thread(target=self.udp_transfer, args=(counter,), daemon=True)
            threads.append(t)
            counter += 1
            t.start()

        for t in threads:
            t.join()

        print(f"{Colors.OKCYAN}All transfers complete, ready for new tests...{Colors.ENDC}\n")


def main():
    """
    Main client function to handle user input, connect to server, and initiate transfers.
    """
    try:
        while True:
            file_size_input = input(f"{Colors.HEADER}Enter file size in bytes (e.g., 1000000 for ~1MB): {Colors.ENDC}")
            if not file_size_input.isdigit():
                print(f"{Colors.WARNING}Invalid file size. Please enter a positive integer.{Colors.ENDC}")
                continue
            file_size = int(file_size_input)

            num_tcp_input = input(f"{Colors.HEADER}Enter number of TCP connections: {Colors.ENDC}")
            if not num_tcp_input.isdigit() or int(num_tcp_input) < 1:
                print(f"{Colors.WARNING}Invalid number of TCP connections. Please enter a positive integer.{Colors.ENDC}")
                continue
            num_tcp = int(num_tcp_input)

            num_udp_input = input(f"{Colors.HEADER}Enter number of UDP connections: {Colors.ENDC}")
            if not num_udp_input.isdigit() or int(num_udp_input) < 1:
                print(f"{Colors.WARNING}Invalid number of UDP connections. Please enter a positive integer.{Colors.ENDC}")
                continue
            num_udp = int(num_udp_input)

            server_ip = input(f"{Colors.HEADER}Enter server IP address: {Colors.ENDC}")
            udp_port_input = input(f"{Colors.HEADER}Enter server UDP port: {Colors.ENDC}")
            tcp_port_input = input(f"{Colors.HEADER}Enter server TCP port: {Colors.ENDC}")

            if not udp_port_input.isdigit() or not tcp_port_input.isdigit():
                print(f"{Colors.WARNING}Invalid port numbers. Please enter valid integers.{Colors.ENDC}")
                continue
            udp_port = int(udp_port_input)
            tcp_port = int(tcp_port_input)

            print(f"{Colors.OKGREEN}Connecting to server at {server_ip} (UDP port {udp_port}, TCP port {tcp_port}){Colors.ENDC}")

            client = Client(server_ip, udp_port, tcp_port, file_size, num_tcp, num_udp)
            client.start_transfers()

            print(f"{Colors.OKCYAN}All transfers complete, ready for new tests...{Colors.ENDC}\n")

    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Client shutting down...{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[Client] Unexpected error: {e}{Colors.ENDC}")
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
