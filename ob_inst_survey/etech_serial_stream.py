"""
Initiates a thread that connects to a serial data stream from an EdgeTech 
deckbox and populates the specified Queue with received strings.
"""
from dataclasses import dataclass
from datetime import datetime
import queue as qu
from threading import Thread

from serial import Serial

SER_TIMEOUT = 0.05


@dataclass
class SerParam:
    """Dataclass for specifying serial connection parameters."""

    port: str = "COM2"
    baud: int = 9600
    stop: int = 1
    parity: str = "N"
    bytesize: int = 8
    turn_time: float = 12.5  # Delay in ms for reply from BPR transducer.
    snd_spd: int = 1500  # Speed of sound in water (typical 1450 to 1570 m/sec)


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
        timeout=SER_TIMEOUT,
    ) as ser:
        print("Connected to EgeTech deckbox: " + ser.portstr)

        while True:
            response_line, _ = get_response(ser)
            if response_line != b"":
                now = datetime.now()
                now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
                response_line = response_line.decode("UTF-8").strip()
                edgetech_q.put(f"{now} {response_line}")


def get_response(ser) -> (str, str):
    """flag variable is only relevant when 8011M is in host mode."""
    response = []
    byte_2 = b""
    byte_1 = b""
    byte_0 = ser.read(1)
    while byte_0 != b"":  # next_byte will be "" after ser.timeout
        response.append(byte_0)
        # byte_2: "*" indicates success, "#" indicates error
        if byte_2 + byte_1 + byte_0 in (b"*\r\n", b"#\r\n"):
            # print("Command completed.")
            flag = b"".join(response[-3:-2])
            response = b"".join(response[0:-4])
            return response, flag
        byte_2 = byte_1
        byte_1 = byte_0
        byte_0 = ser.read(1)
    # If ser.timeout with no terminating success/fail (*/#).
    flag = b"T"
    response = b"".join(response)
    return response, flag


def send_command(ser_conn: SerParam, command: str) -> (str, str):
    """
    Send a serial command to 8011M deckbox and return tuple containing two
    strings (reponse, status flag)
    "*" indicates success
    "#" indicates error
    "T" indicates timeout
    """
    with Serial(
        port=ser_conn.port,
        baudrate=ser_conn.baud,
        parity=ser_conn.parity,
        stopbits=ser_conn.stop,
        bytesize=ser_conn.bytesize,
        timeout=SER_TIMEOUT,
    ) as ser:
        print("Connected to EgeTech deckbox: " + ser.portstr)
        ser.write(command)
        print(f"Sent command: {command}")

        return get_response(ser)
