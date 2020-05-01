import logging
import struct
import asyncio
from enum import IntEnum

from reactivenet import CommandMessage

from . import conf

class Header(IntEnum):
    Result              = 0x00
    Command             = 0x01
    ACK                 = 0x02


async def read_and_forward(reader, writer, queue, lock):
    try:
        header = struct.pack('!B', int(Header.Command))
        msg = await CommandMessage.read(reader)

        packet = header + msg.pack()

        # write first bytes first (header + cmd + len)
        writer.write(packet[:5])
        await writer.drain()
        
        packet = packet[5:]

        packet_len = len(packet)
        logging.debug("Data size (no header fields): {}".format(packet_len))

        # we send only 64 bytes at a time due to limited UART RX buffer.
        # every time the device reads bytes from UART, it sends a dummy byte
        # as an "ACK"
        while packet_len > 0:
            if packet_len <= conf.UART_SEND_BYTES:
                to_send = packet_len
            else:
                to_send = conf.UART_SEND_BYTES

            logging.debug("Sending chunk of {} bytes".format(to_send))

            writer.write(packet[:to_send])
            await writer.drain()

            packet_len -= to_send
            packet = packet[to_send:]

            lock.release()
            await queue.get()
            await lock.acquire()

        return msg.has_response()

    except Exception as e:
        # something went wrong
        logging.warning("[ip] Exception: {}".format(e))
        return False
