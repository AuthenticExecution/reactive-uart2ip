import asyncio
import serial_asyncio
import logging
import functools
import struct
import contextlib

from reactivenet import ResultMessage, CommandMessage

from . import conf
from .ip import *

wait_result = False
# we use a lock to be sure that we don't read and write at the same time in the UART
lock = asyncio.Lock()

class Error(Exception):
    pass

def start_tasks(args):
    loop = asyncio.get_event_loop()

    queue = asyncio.Queue()

    try:
        reader, writer = loop.run_until_complete(
            serial_asyncio.open_serial_connection(url=args.device, baudrate=115200))
    except:
        logging.error("No device connected to {}".format(args.device))
        return

    serial_task = asyncio.ensure_future(run_serial_task(reader, queue))

    server_func = functools.partial(run_network_task, writer, queue)
    server_task = asyncio.start_server(server_func, '0.0.0.0', args.port)
    loop.run_until_complete(server_task)

    try:
        loop.run_until_complete(serial_task)
    except:
        pass
    finally:
        loop.run_until_complete(exit())
        loop.stop()
        loop.close()


async def exit():
    logging.info("Exiting")
    for task in asyncio.Task.all_tasks():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def run_serial_task(reader, queue):
    logging.info("[serial] Initialized")
    while True:
        async with lock:
            try:
                # try to read header
                header = await asyncio.wait_for(reader.read(1), timeout=conf.SERIAL_TIMEOUT)

                header = struct.unpack('!B', header)[0]
                header = Header(header)

                if header == Header.Result and not wait_result:
                    raise Error("[serial] Received unexpected Result header")

                logging.info("[serial] Received message with header {}".format(str(header)))

                if header == Header.Result:
                    msg = await ResultMessage.read(reader)
                    await queue.put(msg)

                elif header == Header.Command:
                    msg = await CommandMessage.read_with_ip(reader)
                    await msg.send()

                elif header == Header.ACK:
                    await queue.put(True) # dummy val to unlock read_and_forward

                else:
                    raise Error("[serial] I don't know what to do with {}".format(str(header)))

                logging.info("[serial] Waiting for next message")

            except asyncio.TimeoutError:
                # nothing to read
                #logging.debug("[serial] nothing to read, retrying after timeout..")
                pass
            except Exception as e:
                logging.error(e)
                break # close program

        await asyncio.sleep(conf.SERIAL_TIMEOUT)



async def run_network_task(serial_writer, queue, reader, writer):
    global wait_result

    logging.info("[ip] New TCP connection")
    # this is a command for sure
    async with lock:
        logging.debug("[ip] got serial lock")
        try:
            has_response = await asyncio.wait_for(
                        read_and_forward(reader, serial_writer, queue, lock),
                        timeout=conf.NETWORK_TIMEOUT
                        )

        except asyncio.TimeoutError:
            # too much time has passed
            logging.debug("[ip] timeout")
            has_response = False

    if has_response:
        wait_result = True
        logging.debug("[ip] Waiting for a response")
        res = await queue.get()
        writer.write(res.pack())

    # otherwise nothing
    wait_result = False
    writer.close()
    await writer.wait_closed()

    logging.info("[ip] Connection closed")
