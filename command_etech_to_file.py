"""
Log EdgeTech deckbox serial responses to a text file.
"""
from datetime import datetime
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
    FILEPATH.mkdir(parents=True, exist_ok=True)
    print(f"Logging to {FILENAME}")

    ser_conn = obsurv.SerParam(port="COM5", baud=9600, timeout=2)

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

            while True:
                cmnd = input("Enter a command to send to the EdgeTech deckbox: ")
                cmnd = cmnd.strip()
                send_command(ser, cmnd)

                while True:
                    sleep(0.001)  # Prevents idle loop from 100% CPU thread usage.
                    response_line, flag = obsurv.get_response(ser)
                    if response_line == b"":
                        # print(".",end="",flush=True)
                        continue

                    now = datetime.now()
                    now = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
                    # Line below fails with this error when deackbox responds
                    # erroneously with non-UTF-8 characters.
                    # UnicodeDecodeError: 'utf-8' codec can't decode byte 0x86 in position 4: invalid start byte
                    # response_line = response_line.decode("UTF-8").strip()
                    flag = flag.decode("UTF-8").strip()

                    with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
                        log_file.write(f"{response_line} {flag}\n")
                        print(f"{response_line} {flag}")
                        break

    except KeyboardInterrupt:
        sys.exit("*** End EdgeTech Command Logging ***")
    except SerialException as error:
        sys.exit(error)


def send_command(ser, command):
    """Format string as bytes and send to serial port."""
    command = f"{command}\r\n".encode("UTF-8")
    ser.write(command)
    with open(FILENAME, "a+", newline="", encoding="utf-8") as log_file:
        log_file.write(f"Command: {command}\n")
    print(f"Command: {command}")

    return


if __name__ == "__main__":
    main()
