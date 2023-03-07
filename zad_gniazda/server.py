import socket
from threading import Thread
from utils import Logger, receive_message, encode_message


class Server:
    USERNAME = 2
    SOCKET = 1
    ADDRESS = 0

    def __init__(self, server_port: int, server_host: str = 'localhost'):
        self.tcp_thread = None
        self.udp_thread = None
        self._server_port = server_port
        self._server_host = server_host

        self._connected_clients = dict()

        self._tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        self._udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        try:
            self._tcp_socket.bind((self._server_host, self._server_port))
            self._udp_socket.bind((self._server_host, self._server_port))
        except OSError:
            Logger.error("Address already taken")
            exit(1)

        self.run_threads = True

        Logger.info("Server initiated successfully")

    def _accept_tcp_connections(self):
        self._tcp_socket.listen()
        while self.run_threads:
            client_socket, client_address = self._tcp_socket.accept()
            client_ip, client_port = client_address

            client_id = 0
            while not client_id or client_id in self._connected_clients:
                client_id += 1

            self._connected_clients[client_id] = dict()
            self._connected_clients[client_id][Server.SOCKET] = client_socket
            self._connected_clients[client_id][Server.ADDRESS] = client_address

            Thread(target=self._handle_tcp_client, args=(client_id,)).start()

            Logger.info(f"New client {client_ip}:{client_port} connected successfully with id={client_id}")

    def _handle_tcp_client(self, client_id):
        client_address = self._connected_clients[client_id][Server.ADDRESS]
        client_socket = self._connected_clients[client_id][Server.SOCKET]

        nickname = receive_message(client_socket)
        self._connected_clients[client_id][Server.USERNAME] = nickname

        client_socket.send(f"{client_id}".encode('utf-8'))

        while self.run_threads:
            client_message = receive_message(client_socket)

            if not client_message:
                self.remove_client(client_id)
                break

            message = f"{nickname}#{client_id}> {client_message}"
            Logger.info(f"TCP: {message}")

            encoded_message = encode_message(message)
            for client_info in self._connected_clients.values():
                socket = client_info[Server.SOCKET]
                if socket != client_socket:
                    socket.sendall(encoded_message)

    def _receive_udp(self):
        while self.run_threads:
            client_message, client_address = self._udp_socket.recvfrom(1024)
            client_message = client_message.decode('utf-8')

            client_id = None
            nickname = None
            for id, client_info in self._connected_clients.items():
                if client_info[Server.ADDRESS] == client_address:
                    client_id = id
                    nickname = client_info[Server.USERNAME]

            message = f"{nickname}#{client_id}> {client_message}"
            Logger.info(f"UDP: {message}")

            message = message.encode('utf-8')
            for client_info in self._connected_clients.values():
                if client_info[Server.ADDRESS] != client_address:
                    self._udp_socket.sendto(message, client_info[Server.ADDRESS])

    def remove_client(self, client_id):
        if client_id in self._connected_clients:
            self._connected_clients[client_id][Server.SOCKET].close()
            del self._connected_clients[client_id]
            Logger.info(f"Client with id={client_id} removed")

    def listen(self):
        self.tcp_thread = Thread(target=self._accept_tcp_connections, args=(), daemon=True)
        self.tcp_thread.start()

        self.udp_thread = Thread(target=self._receive_udp, args=(), daemon=True)
        self.udp_thread.start()

        Logger.info(f"Server is listening on {self._server_host}:{self._server_port}")

        self.tcp_thread.join()
        self.udp_thread.join()

    def stop(self):
        self.run_threads = False

        self._udp_socket.close()
        self._tcp_socket.close()

        connected_client_ids = {key for key in self._connected_clients.keys()}
        for client_id in connected_client_ids:
            self.remove_client(client_id)


if __name__ == '__main__':
    SERVER_PORT = 8000
    server = Server(SERVER_PORT)
    try:
        server.listen()
    finally:
        server.stop()
