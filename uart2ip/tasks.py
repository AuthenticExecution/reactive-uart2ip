import asyncio
import serial_asyncio
import logging
import functools
import struct
import contextlib

from reactivenet import ResultMessage, CommandMessage

from . import conf
from .ip import Header, read_and_forward

# we use a lock to be sure that we don't read and write at the same time in the UART
serial_lock = asyncio.Lock()
# we use another lock to be sure that only one external entity at a time uses the UART
network_lock = asyncio.Lock()

# Dict with result messages received
results = {}

async def get_result(id):
    #logging.debug("Waiting for ID: {}".format(id))
    while True:
        if id in results:
            break
        await asyncio.sleep(conf.WAIT_RESULT)

    return results.pop(id)

def add_result(id, res):
    #logging.debug("ID: {}".format(id))
    results[id] = res


class Error(Exception):
    pass

def start_tasks(args):
    loop = asyncio.get_event_loop()

    try:
        reader, writer = loop.run_until_complete(
            serial_asyncio.open_serial_connection(url=args.device, baudrate=conf.BAUD_RATE))
    except:
        logging.error("No device connected to {}".format(args.device))
        return

    serial_task = asyncio.ensure_future(run_serial_task(reader))

    server_func = functools.partial(run_network_task, reader, writer)
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


async def run_serial_task(reader):
    logging.info("[serial] Initialized")
    while True:
        async with serial_lock:
            try:
                # try to read header
                header = await asyncio.wait_for(reader.readexactly(1), timeout=conf.SERIAL_TIMEOUT)

                header = struct.unpack('!B', header)[0]
                header = Header(header)

                logging.info("[serial] Received message with header {}".format(str(header)))

                if header == Header.Result:
                    id = await reader.readexactly(conf.CMD_ID_SIZE) # result id
                    id = struct.unpack(conf.CMD_ID_PACK, id)[0]
                    msg = await ResultMessage.read(reader)
                    add_result(id, msg)

                elif header == Header.Command:
                    msg = await CommandMessage.read_with_ip(reader)
                    await msg.send()

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



async def run_network_task(serial_reader, serial_writer, reader, writer):
    async with network_lock:
        logging.info("[ip] New TCP connection")
        # this is a command for sure
        async with serial_lock:
            logging.debug("[ip] got serial lock")
            try:
                has_response, id = await asyncio.wait_for(
                            read_and_forward(reader, serial_reader, serial_writer),
                            timeout=conf.NETWORK_TIMEOUT
                            )

            except asyncio.TimeoutError:
                # too much time has passed
                logging.debug("[ip] timeout")
                has_response = False

        if has_response:
            logging.debug("[ip] Waiting for a response")
            res = await get_result(id)
            writer.write(res.pack())

        # otherwise nothing
        writer.close()
        await writer.wait_closed()

        logging.info("[ip] Connection closed")
