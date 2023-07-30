"""
Initiates a thread that connects to an NMEA data stream via UDP or TCP and
populates the specified Queue with NMEA strings.
"""
from dataclasses import dataclass
import queue as qu
import re
import socket
import sys
from threading import Thread


@dataclass
class IpParam:
    """Dataclass for specifying IP connection parameters."""

    port: int
    addr: str = "127.0.0.1"  # local for UDP / remote for TCP
    prot: str = "UDP"
    buffer: int = 2048

    def __post_init__(self):
        # Validate IP Protocol
        self.prot = self.prot.lower()
        if self.prot not in ("udp", "tcp"):
            raise ValueError(
                f"{self.prot} is not a valid protocol. Must be either 'UDP' or 'TCP'."
            )

        # Validate IP address
        if not re.match(
            r"^(([01]\d{0,2})|(2(\d?|([0-4]\d)|(5[0-5]))))"
            r"(\.(([01]\d{0,2})|(2(\d?|([0-4]\d)|(5[0-5]))))){3}$",
            self.addr,
        ):
            raise ValueError(f"{self.addr} is not a valid IP address.")


def ip_stream(ip_conn: IpParam, nmea_q: qu.Queue[str]):
    """Initiate a queue receiving an NMEA data stream."""
    if ip_conn.prot == "udp":
        Thread(target=__receive_udp, args=(ip_conn, nmea_q), daemon=True).start()
    elif ip_conn.prot == "tcp":
        Thread(target=__receive_tcp, args=(ip_conn, nmea_q), daemon=True).start()


def __receive_udp(udp_conn: IpParam, nmea_q: qu.Queue[str]):
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
                nmea_lines = __msg_to_sentences(message)
                for line in nmea_lines:
                    nmea_q.put(line)


def __receive_tcp(tcp_conn: IpParam, nmea_q: qu.Queue[str]):
    """
    Connect to TCP server and populate nmea_q with NMEA sentences.
    If a TCP timeout error it will populate nmea_q with str "TimeoutError".
    """
    while True:
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
                except TimeoutError:
                    print(
                        f"TCP server {tcp_conn.addr}:{tcp_conn.port} is not "
                        f"available. Exiting!"
                    )
                    nmea_q.put("TimeoutError")
                    sys.exit()

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
            while True:
                message = nmea_client.recv(tcp_conn.buffer)
                if message:
                    nmea_lines = __msg_to_sentences(message)
                    for line in nmea_lines:
                        nmea_q.put(line)
                else:
                    print(
                        f"*** DISCONNECTED from TCP server."
                        f"{tcp_conn.addr}:{tcp_conn.port}."
                    )
                    break


def __msg_to_sentences(message: str) -> list[str]:
    message = message.decode("utf-8")
    nmea_sentences = []
    for sentence in message.splitlines():
        nmea_sentences.append(sentence.strip())

    return nmea_sentences
