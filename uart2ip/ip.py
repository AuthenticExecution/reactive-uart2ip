import logging
import struct
import asyncio
from enum import IntEnum

from reactivenet import CommandMessage

from . import conf

handshake_header = None


class Header(IntEnum):
    Result = 0x00
    Command = 0x01
    ACK = 0x02


def get_handshake_header():
    global handshake_header

    if handshake_header is None:
        return None

    tmp = handshake_header
    handshake_header = None

    return tmp


async def handshake(reader, writer, serial_lock):
    global handshake_header

    # send handshake dummy byte
    dummy = b'\xff'

    writer.write(dummy)
    await writer.drain()

    while True:
        res = await reader.readexactly(1)

        if dummy == res:
            break

        # If we are here, it means that we have read a byte belonging to another
        # packet (a RemoteOutput sent from Sancus to the external world)
        logging.debug(
            "[ip] stopping handshake, there is an incoming packet from UART")
        handshake_header = res

        # release serial lock, and then wait until the serial task processes
        # the incoming packet. after that (or, after all packets are read),
        # we should receive the handshake response we were expecting
        serial_lock.release()
        while handshake_header is not None:
            await asyncio.sleep(conf.SLEEP_TIME)
        await serial_lock.acquire()
        logging.debug("[ip] resumed handshake")


async def read_and_forward(reader, serial_reader, serial_writer, serial_lock):
    try:
        header = struct.pack('!B', int(Header.Command))
        msg = await CommandMessage.read(reader)

        packet = header + msg.pack()

        await handshake(serial_reader, serial_writer, serial_lock)

        # write first bytes first (header + cmd + len)
        serial_writer.write(packet[:5])
        await serial_writer.drain()

        packet = packet[5:]

        packet_len = len(packet)
        logging.debug(f"Data size (no header fields): {packet_len}")

        # we send only N bytes at a time due to limited UART RX buffer.
        # every time the device reads bytes from UART, it sends a dummy byte
        # as an "ACK"
        while packet_len > 0:
            if packet_len <= conf.UART_SEND_BYTES:
                to_send = packet_len
            else:
                to_send = conf.UART_SEND_BYTES

            serial_writer.write(packet[:to_send])
            await serial_writer.drain()

            packet_len -= to_send
            packet = packet[to_send:]

            await serial_reader.readexactly(1)  # ack
            await asyncio.sleep(conf.SLEEP_TIME)

        return msg.has_response()

    except Exception as e:
        # something went wrong
        logging.warning(f"[ip] Exception: {e}")
        return False
