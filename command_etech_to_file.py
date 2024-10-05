"""Log EdgeTech deckbox serial responses to a text file."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

from serial import Serial, SerialException

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
FILEPREFIX = "edgetech"
FILEPATH = Path("./logs/edgetech/")
FILENAME = FILEPATH / f"{FILEPREFIX}_{TIMESTAMP_START}.txt"


def main(ser_conn=obsurv.SerParam):
    """Initialise EdgeTech data stream and log to text file."""
    u_range_gate = 3500  # milliseconds
    # Set serial timout to be greater of upper range gate plus a little extra
    # the or time required to transmir BACS command.
    serial_timeout = 0.5 + u_range_gate / 1000
    if serial_timeout < 11:
        serial_timeout = 11

    FILEPATH.mkdir(parents=True, exist_ok=True)
    print(f"Logging to {FILENAME}")

    ser_conn = obsurv.SerParam(port="COM5", baud=9600, timeout=serial_timeout)

    try:
        with Serial(
            port=ser_conn.port,
            baudrate=ser_conn.baud,
            parity=ser_conn.parity,
            stopbits=ser_conn.stop,
            bytesize=ser_conn.bytesize,
            timeout=ser_conn.timeout,
        ) as ser:
            print(
                f"Connected to EgeTech deckbox: {ser.portstr} at {ser.baudrate} baud."
            )

            # Send CR/LF to put deckbox into Host mode for receiving commands.
            command = ""
            send_command(ser, command)

            ser.timeout = 0.1
            response, flag = get_response(ser)
            ser.timeout = ser_conn.timeout
            if flag == b"#":
                print("Deckbox already in Host Mode.")
                print(f"Response: {response}")

            # Set an upper range gate because if not set the range request
            # never times out.
            command = f"ug{u_range_gate:05d}"
            send_command(ser, command)
            ser.timeout = 0.1
            response, flag = get_response(ser)
            ser.timeout = ser_conn.timeout

            while True:
                cmnd = input("Enter a command to send to the EdgeTech deckbox: ")
                cmnd = cmnd.strip()
                send_command(ser, cmnd)
                stop_at_next = False

                while True:
                    sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                    response_line, flag = get_response(ser)
                    if response_line == b"":
                        if stop_at_next:
                            break
                        continue
                    ser.timeout = serial_timeout

                    now = datetime.now(timezone.utc)
                    now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
                    flag = flag.decode("UTF-8").strip()

                    with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
                        log_file.write(f"{response_line} {flag}\n")
                    if flag == ".":
                        ser.write(b" ")  # Cancel listening for BACS command.
                    elif flag == "S":
                        # If response received is a range time value then
                        # it may or may not have a following * or # flag.
                        ser.timeout = 0.1
                        stop_at_next = True
                    else:
                        break

    except KeyboardInterrupt:
        sys.exit("*** End EdgeTech Command Logging ***")
    except SerialException as error:
        sys.exit(error)


def send_command(ser, command):
    """Format string as bytes and send to serial port."""
    # Only append '\r' to the command (not '\r\n'). An extra '\n' is being
    # appended to end of ser.write loop elsewhere (not sure how/where).
    command = f"{command.strip().upper()}\r"
    # print("Command: ", end="")
    for byte in command:
        byte = byte.encode("UTF-8")
        ser.write(byte)
        # print(f"{byte} ", end="", flush=True)
        sleep(0.001)  # Delay needed for deckbox to correctly receive command.
    # print()

    with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
        log_file.write(f"Command: {command}\n")

    return


def get_response(ser) -> tuple[str, str]:
    """Flag variable is only relevant when 8011M is in host mode."""
    response = []
    flag = ""
    byte_2 = b""
    byte_1 = b""
    byte_0 = ser.read(1)
    while byte_0 != b"":  # next_byte will be "" after ser.timeout
        response.append(byte_0)
        print(byte_0.decode("UTF-8"), end="", flush=True)
        byte_tail = byte_2 + byte_1 + byte_0
        # byte_2: "*" indicates success, "#" indicates error
        if byte_tail in (b"*\r\n", b"#\r\n", b"S\r\n") or (
            byte_tail == b"..." and (b"".join(response[-9:]) == b"." * 9)
        ):
            flag = response[-3]
            response = b"".join(response)
            return response, flag
        byte_2 = byte_1
        byte_1 = byte_0
        byte_0 = ser.read(1)
    # If ser.timeout with no terminating success/fail (*/#/S).
    flag = b"T"
    response = b"".join(response)
    return response, flag


if __name__ == "__main__":
    main()
