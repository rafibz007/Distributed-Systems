import pickle
import struct


class Logger:
    @staticmethod
    def info(message: str):
        print(f"[+] {message}")

    @staticmethod
    def debug(message: str):
        print(f"[?] {message}")

    @staticmethod
    def error(message: str):
        print(f"[!] {message}")


def encode_message(data: str):
    serialized_data = pickle.dumps(data)
    return struct.pack('>I', len(serialized_data)) + serialized_data


def receive_message(connection):
    try:
        data_size = struct.unpack('>I', connection.recv(4))[0]
        received_payload = b""
        remaining_payload_size = data_size
        while remaining_payload_size != 0:
            received_payload += connection.recv(remaining_payload_size)
            remaining_payload_size = data_size - len(received_payload)
        data = pickle.loads(received_payload)
    except (OSError, struct.error):
        data = b''

    return data
