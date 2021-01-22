# reactive-uart2ip

Application that works as a "bridge" between the Sancus FPGA (through UART) and an external client using TCP/IP. This is implemented with the specific purpose to handle Authentic Execution messages, hence this application is not "general purpose", but strongly dependent to the Sancus application running inside the FPGA.

## Installation

```bash
# Install reactive-uart2ip - you must be in the root of this repository
pip install .

# run reactive-uart2ip
### <loglevel>: log level, e.g., "debug". Default "info"
### <device>: UART device. Default "/dev/ttyUSB1"
### <port>: port used by the app to listen for TCP connections
reactive-uart2ip -l <loglevel> -d <device> -p <port>
```

## Run reactive-uart2ip with Docker

```bash
# Run the reactive-uart2ip Docker image
### <loglevel>, <device> and <port> are the same as above
make run LOG=<loglevel> DEVICE=<device> PORT=<port>
```

## How it works

The application is implemented using `asyncio` tasks.

### Serial task

A first task reads for messages from the **serial** communication. 

- The messages can either be commands or results (see [reactive-net](https://github.com/gianlu33/reactive-net))
- A `Command` received from the device is immediately sent to the destination (ip and port are received as well), and there is **no response**.
  - Sancus only sends `RemoteOutput` commands
- A `Result` of a command previously sent to the device is added to a queue, where the task of the TCP connection that has sent the command will retrieve and send back to the client.

### TCP/IP tasks

For each new TCP connection, an asynchronous task is created, but **only one task at a time** uses the UART (by means of a lock).

- Each TCP connection has the purpose to send a command to the device. If the command expects a result, the task will wait until it is received (without releasing the lock). A timeout is set to avoid endless wait of other tasks, but this should never happen in a normal situation.
- Before starting the transmission of the data, a *handshake* is performed. This is necessary to "wake up" the device, in order not to lose bytes during the transmission. The handshake consists on the exchange of one single dummy byte between the application and the FPGA.
- Since the FPGA has a RX buffer limited to 127 bytes, we need to split large packets in several chunks. In order not to lose any bytes, the FPGA sends an *ACK* byte after each chunk received. The application, after sending the chunk, waits for the ACK, and after that continues the transmission.