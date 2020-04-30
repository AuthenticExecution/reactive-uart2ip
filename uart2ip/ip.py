import logging
import struct
import asyncio
from enum import IntEnum

from reactivenet import CommandMessage

from . import conf

class Header(IntEnum):
    Result              = 0x00
    Command             = 0x01


async def read_and_forward(reader, writer):
    try:
        header = struct.pack('!B', int(Header.Command))
        msg = await CommandMessage.read(reader)

        writer.write(header + msg.pack())

        return msg.has_response()

    except Exception as e:
        # something went wrong
        logging.warning("[ip] Exception: {}".format(e))
        return False
