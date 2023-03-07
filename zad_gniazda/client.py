import select
import socket
from threading import Thread

from utils import encode_message, receive_message, Logger


class Client:
    def __init__(self, server_port: int, server_host: str, nickname: str, multicast_port: int, multicast_group: str):
        self._server_port = server_port
        self._server_host = server_host
        self._nickname = nickname
        self._multicast_port = multicast_port
        self._multicast_group = multicast_group

        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._tcp_socket.connect((self._server_host, self._server_port))
        self._tcp_socket.send(encode_message(nickname))
        self.id = int(self._tcp_socket.recv(8).decode('utf-8'))

        _, self._client_port = self._tcp_socket.getsockname()

        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._udp_socket.bind(('', self._client_port))

        self._udp_multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self._udp_multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._udp_multicast_socket.bind((self._multicast_group, self._multicast_port))

        Thread(target=self.listen, args=(), daemon=True).start()

    def send_tcp(self, message: str):
        encoded_message = encode_message(message)
        self._tcp_socket.sendall(encoded_message)

    def send_udp(self, message: str):
        self._udp_socket.sendto(message.encode('utf-8'), (self._server_host, self._server_port))

    def send_multicast_udp(self, message: str):
        self._udp_multicast_socket.sendto(f"{self._nickname}#{self.id}>{message}".encode('utf-8'), (self._multicast_group, self._multicast_port))

    def close(self):
        self._udp_multicast_socket.close()
        self._tcp_socket.close()
        self._udp_socket.close()

    def listen(self):
        while True:
            selected_sockets, _, _ = select.select([self._tcp_socket, self._udp_socket, self._udp_multicast_socket], [],
                                                   [])

            if self._tcp_socket in selected_sockets:
                message = receive_message(self._tcp_socket)

                if not message:
                    Logger.error("Server disconnected")
                    exit(1)

                print(f'[TCP] {message}')

            if self._udp_socket in selected_sockets:
                message, _ = self._udp_socket.recvfrom(1024)
                message = message.decode('utf-8')
                print(f'[UDP] {message}')

            if self._udp_multicast_socket in selected_sockets:
                message, _ = self._udp_multicast_socket.recvfrom(1024)
                message = message.decode('utf-8')
                print(f'[MULTICAST] {message}')


if __name__ == '__main__':
    SERVER_PORT = 8000
    SERVER_HOST = 'localhost'
    MULTICAST_PORT = 8001
    MULTICAST_GROUP = "224.0.0.1"

    nickname = None
    while not nickname:
        nickname = input("Your name: ")

    client = Client(SERVER_PORT, SERVER_HOST, nickname, MULTICAST_PORT, MULTICAST_GROUP)

    TCP = 't'
    UDP = 'u'
    MULTICAST = 'm'
    while True:
        try:
            line = input()
        except KeyboardInterrupt:
            client.close()
            exit(1)

        if not line:
            continue

        if line.startswith('/'):
            first, *rest = line.split(' ', 1)
            command = first[1:].lower()
            message = ''.join(rest)
        else:
            command, message = TCP, line

        if command == TCP:
            client.send_tcp(message)
        elif command == UDP:
            client.send_udp(message)
        elif command == MULTICAST:
            client.send_multicast_udp(message)
        else:
            print(f'Invalid command /{command}')
