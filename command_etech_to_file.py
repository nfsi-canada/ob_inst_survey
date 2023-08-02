"""
Log EdgeTech deckbox serial responses to a text file.
"""
from datetime import datetime, timedelta
from pathlib import Path
import sys
from time import sleep

from serial import Serial, SerialException

import ob_inst_survey as obsurv

TIMESTAMP_START = datetime.now().strftime("%Y-%m-%d_%H-%M")
FILEPREFIX = "edgetech"
FILEPATH = Path("./logs/edgetech/")
FILENAME = FILEPATH / f"{FILEPREFIX}_{TIMESTAMP_START}.txt"


def main(ser_conn=obsurv.IpParam):
    """
   Initialise EdgeTech data stream and log to text file.
    """
    u_range_gate = 500
    serial_timeout = 0.5 + u_range_gate/1000
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
            print(f"Connected to EgeTech deckbox: {ser.portstr} at {ser.baudrate} baud.")

            # Send CR/LF to put deckbox into Host mode for receiving commands.
            command = ""
            send_command(ser, command)

            ser.timeout = 0.1
            response, flag = obsurv.get_response(ser)
            ser.timeout = ser_conn.timeout
            if flag == b"#":
                print("Deckbox already in Host Mode.")
                print(f"Response: {response}")

            command = f"ug{u_range_gate:05d}"
            send_command(ser, command)
            ser.timeout = 0.1
            response, flag = obsurv.get_response(ser)
            ser.timeout = ser_conn.timeout

            while True:
                cmnd = input("Enter a command to send to the EdgeTech deckbox: ")
                cmnd = cmnd.strip()
                send_command(ser, cmnd)
                stop_at_next = False

                while True:
                    sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                    response_line, flag = obsurv.get_response(ser)
                    if response_line == b"":
                        if stop_at_next:
                            break
                        continue
                    ser.timeout=serial_timeout

                    now = datetime.now()
                    now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
                    flag = flag.decode("UTF-8").strip()

                    with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
                        log_file.write(f"{response_line} {flag}\n")
                    if flag == ".":
                        ser.write(b" ") # Cancel listening for BACS command.
                    elif flag == "S":
                        # If response is a range time (IN or GR command) then
                        # it may or may not have a following * or # flag.
                        ser.timeout=0.1
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


if __name__ == "__main__":
    main()
