"""
Verify checksum for an NMEA sentence.
"""
import re


def nmea_checksum(sentence: str) -> bool:
    """Returns True if NMEA sentence checksum is valid, otherwise False."""
    sentence_match = re.match(r"\$(.*)\*(.{2})", sentence)
    chksumdata = sentence_match[1]
    chksum = int(sentence_match[2], 16)  # convert from hex string
    check = 0

    # For each char in chksumdata, XOR against the previous XOR'd char.
    # The final XOR of the last char will be our checksum to verify
    # against the checksum we sliced off the NMEA sentence.
    for char in chksumdata:
        # XOR'ing value of csum against the next char in line
        # and storing the new XOR value in csum
        check ^= ord(char)

    # Do we have a validated sentence?
    return check == chksum
