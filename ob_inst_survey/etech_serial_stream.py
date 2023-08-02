"""
Initiates a thread that connects to a serial data stream from an EdgeTech 
deckbox and populates the specified Queue with received strings.
"""
from dataclasses import dataclass
from datetime import datetime as dt
import queue as qu
from threading import Thread

from serial import Serial


@dataclass
class SerParam:
    """Dataclass for specifying serial connection parameters."""

    port: str = "COM2"
    baud: int = 9600
    stop: int = 1
    parity: str = "N"
    bytesize: int = 8
    timeout: float = 0.05


def etech_serial_stream(ser_conn: SerParam, edgetech_q: qu.Queue[str]):
    """Initiate a queue receiving an EdgeTech deckbox data stream."""
    Thread(target=__receive_serial, args=(ser_conn, edgetech_q), daemon=True).start()


def __receive_serial(ser_conn: SerParam, edgetech_q: qu.Queue[str]):
    with Serial(
        port=ser_conn.port,
        baudrate=ser_conn.baud,
        parity=ser_conn.parity,
        stopbits=ser_conn.stop,
        bytesize=ser_conn.bytesize,
        timeout=ser_conn.timeout,
    ) as ser:
        print(f"Connected to EgeTech deckbox: {ser.portstr} at {ser.baudrate} baud.")

        while True:
            response_line = get_response(ser)
            if response_line != b"":
                now = dt.now()
                now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
                response_line = response_line.decode("UTF-8").strip()
                edgetech_q.put(f"{now} {response_line}")


def get_response(ser) -> str:
    response = []
    byte_next = ser.read(1)
    while byte_next != b"":  # next_byte will be "" after ser.timeout
        response.append(byte_next)
        print(byte_next.decode("UTF-8"), end="", flush=True)
    response = b"".join(response)
    return response
