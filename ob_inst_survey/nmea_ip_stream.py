"""
Initiates a thread that connects to an NMEA data stream via UDP or TCP and
populates the specified Queue with NMEA strings.
"""
from dataclasses import dataclass
from queue import Queue
import re
import socket
import sys
from threading import Thread


@dataclass
class IpParam:
    """
    Dataclass for specifying IP connection parameters.
    For TCP the IP address is the remote server
    For UDP the IP address is a/the valid local host address (ie one of):
      "0.0.0.0"
      "127.0.0.1"
      socket.gethostbyname(socket.gethostname())
      If more than one local NIC then the IP address of the actual NIC to be
      used for receieving UDP stream is required.
    """

    port: int = 50001
    addr: str = "127.0.0.1"  # local for UDP / remote for TCP
    prot: str = "UDP"
    buffer: int = 2048

    def __post_init__(self):
        # Validate IP Protocol
        self.prot = self.prot.upper()
        if self.prot not in ("UDP", "TCP"):
            raise ValueError(
                f"{self.prot} is not a valid protocol. Must be either 'UDP' or 'TCP'."
            )

        # Validate IP address
        if not re.match(
            r"^(([01]\d{0,2})|[2-9]\d?|(2(([0-4]\d)|(5[0-5]))))"
            r"(\.(([01]\d{0,2})|[2-9]\d?|(2(([0-4]\d)|(5[0-5]))))){3}$",
            self.addr,
        ):
            raise ValueError(f"{self.addr} is not a valid IP address.")


def nmea_ip_stream(ip_conn: IpParam, nmea_q: Queue[str]):
    """Initiate a queue receiving an NMEA data stream."""
    if ip_conn.prot == "UDP":
        Thread(target=_receive_udp, args=(ip_conn, nmea_q), daemon=True).start()
    elif ip_conn.prot == "TCP":
        Thread(target=_receive_tcp, args=(ip_conn, nmea_q), daemon=True).start()


def _receive_udp(udp_conn: IpParam, nmea_q: Queue[str]):
    """Listen on UDP port and populate queue with NMEA stream."""
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM) as nmea_server:
        nmea_server.bind((udp_conn.addr, udp_conn.port))
        print(
            f"Listening for UDP stream locally on "
            f"{udp_conn.addr}:{udp_conn.port}..."
        )

        # Listen for incomming datagrams
        while True:
            message = nmea_server.recv(udp_conn.buffer)
            if message:
                nmea_lines = _msg_to_sentences(message)
                for line in nmea_lines:
                    nmea_q.put(line)


def _receive_tcp(tcp_conn: IpParam, nmea_q: Queue[str]):
    """
    Connect to TCP server and populate nmea_q with NMEA sentences.
    If a TCP timeout error it will populate nmea_q with str "TimeoutError".
    """
    timeout_notified = False
    while True:
        try:
            with socket.socket(
                family=socket.AF_INET, type=socket.SOCK_STREAM
            ) as nmea_client:
                conn_rfsd_notified = False
                while True:
                    try:
                        nmea_client.settimeout(5)
                        nmea_client.connect((tcp_conn.addr, tcp_conn.port))
                        nmea_client.settimeout(None)
                        break
        
                    except (ConnectionRefusedError, ConnectionAbortedError):
                        if not conn_rfsd_notified:
                            print(
                                f"*** TCP server {tcp_conn.addr}:{tcp_conn.port} is not "
                                f"currently providing a connection. Waiting..."
                            )
                            conn_rfsd_notified = True
                print(
                    f"*** Connected to TCP server at " f"{tcp_conn.addr}:{tcp_conn.port}."
                )

                # Listen for incomming data stream
                conn_rfsd_notified = False
                while True:
                    message = nmea_client.recv(tcp_conn.buffer)
                    if message:
                        nmea_lines = _msg_to_sentences(message)
                        for line in nmea_lines:
                            nmea_q.put(line)
                    else:
                        print(
                            f"*** DISCONNECTED from TCP server."
                            f"{tcp_conn.addr}:{tcp_conn.port}."
                        )

        except ConnectionAbortedError:
            print(
                f"Connection to TCP server {tcp_conn.addr}:{tcp_conn.port} was "
                f"aborted. Attempting to reconnect..."
            )

        except TimeoutError:
            if not timeout_notified:
                print(
                    f"TCP server {tcp_conn.addr}:{tcp_conn.port} is not "
                    f"available. Waiting..."
                )
                timeout_notified = True

        except OSError as err:
            print(f"{err}")



def _msg_to_sentences(message: str) -> list[str]:
    message = message.decode("utf-8")
    nmea_sentences = []
    for sentence in message.splitlines():
        nmea_sentences.append(sentence.strip())

    return nmea_sentences
