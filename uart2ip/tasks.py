import asyncio
import logging
import functools
import struct
import contextlib
import serial_asyncio

from reactivenet import ResultMessage, CommandMessage

from . import conf
from .ip import Header, read_and_forward, get_handshake_header

# we use this lock to be sure that we don't read and write at the same time in the UART
serial_lock = asyncio.Lock()

# we use this lock to be sure that only one external entity at a time uses the UART
network_lock = asyncio.Lock()


class Error(Exception):
    pass


def start_tasks(args):
    loop = asyncio.get_event_loop()

    queue = asyncio.Queue()

    try:
        reader, writer = loop.run_until_complete(
            serial_asyncio.open_serial_connection(url=args.device,
                                                  baudrate=args.baudrate))
    except:
        logging.error(f"No device connected to {args.device}")
        return

    serial_task = asyncio.ensure_future(run_serial_task(reader, queue))

    server_func = functools.partial(run_network_task, reader, writer, queue)
    server_task = asyncio.start_server(server_func, '0.0.0.0', args.port)
    loop.run_until_complete(server_task)

    try:
        loop.run_until_complete(serial_task)
    except:
        pass
    finally:
        loop.run_until_complete(exit_app())
        loop.stop()
        loop.close()


async def exit_app():
    logging.info("Exiting")
    for task in asyncio.all_tasks():
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


async def run_serial_task(reader, queue):
    logging.info("[serial] Initialized")
    while True:
        async with serial_lock:
            try:
                # try to read header
                header = get_handshake_header()
                if header is None:
                    header = await asyncio.wait_for(
                        reader.readexactly(1),
                        timeout=conf.SERIAL_TIMEOUT)

                header = struct.unpack('!B', header)[0]
                header = Header(header)

                logging.info(f"[serial] Received message with header {str(header)}")

                if header == Header.Result:
                    msg = await ResultMessage.read(reader)
                    await queue.put(msg)

                elif header == Header.Command:
                    msg = await CommandMessage.read_with_ip(reader)
                    await msg.send()

                else:
                    raise Error(f"[serial] I don't know what to do with {str(header)}")

                logging.info("[serial] Waiting for next message")

            except asyncio.TimeoutError:
                #logging.debug("[serial] nothing to read, retrying after timeout..")
                pass
            except Exception as e:
                logging.error(e)
                break  # close program

        await asyncio.sleep(conf.SLEEP_TIME)


async def run_network_task(serial_reader, serial_writer, queue, reader, writer):
    async with network_lock:
        logging.info("[ip] New TCP connection")

        async with serial_lock:
            logging.debug("[ip] got serial lock")
            try:
                has_response = await asyncio.wait_for(
                    read_and_forward(
                        reader, serial_reader, serial_writer, serial_lock),
                    timeout=conf.NETWORK_TIMEOUT
                )

            except asyncio.TimeoutError:
                # too much time has passed
                logging.warning("[ip] timeout")
                has_response = False

        if has_response:
            try:
                logging.debug("[ip] Waiting for a response")
                res = await asyncio.wait_for(
                    queue.get(),
                    timeout=conf.NETWORK_TIMEOUT
                )

                writer.write(res.pack())

            except asyncio.TimeoutError:
                # too much time has passed
                logging.warning("[ip] timeout")

        writer.close()
        try:
            await writer.wait_closed()
        except:
            # old Python version
            pass

        logging.info("[ip] Connection closed")
