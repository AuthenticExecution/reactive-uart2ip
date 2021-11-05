import argparse
import logging
import os
import colorlog

from . import conf


def _set_parser():
    parser = argparse.ArgumentParser(description='Authentic Execution SGX')
    parser.add_argument('-l', '--loglevel', nargs='?',
                        default=conf.DEFAULT_LOG_LEVEL, type=__log_level)
    parser.add_argument('-d', '--device', required=False,
                        default=conf.DEFAULT_DEVICE, help='Device path (e.g. /dev/ttyUSB1)')
    parser.add_argument('-b', '--baudrate', required=False,
                        default=conf.BAUD_RATE, type=int, help='Baud Rate (e.g. 115200)')
    parser.add_argument('-p', '--port', required=True,
                        type=__int16bits, help='TCP port of the node')

    return parser


def _set_logging(loglevel):
    log = logging.getLogger()

    format_str = '%(asctime)s.%(msecs)03d - %(levelname)-8s: %(message)s'
    date_format = '%H:%M:%S'  # '%Y-%m-%d %H:%M:%S'
    if os.isatty(2):
        cformat = '%(log_color)s' + format_str
        colors = {'DEBUG': 'reset',
                  'INFO': 'bold_green',
                  'WARNING': 'bold_yellow',
                  'ERROR': 'bold_red',
                  'CRITICAL': 'bold_red'}
        formatter = colorlog.ColoredFormatter(cformat, date_format,
                                              log_colors=colors)
    else:
        formatter = logging.Formatter(format_str, date_format)

    log.setLevel(loglevel)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    log.addHandler(stream_handler)


def __log_level(arg):
    arg = arg.lower()

    if arg == "critical":
        return logging.CRITICAL
    if arg == "error":
        return logging.ERROR
    if arg == "warning":
        return logging.WARNING
    if arg == "info":
        return logging.INFO
    if arg == "debug":
        return logging.DEBUG
    if arg == "notset":
        return logging.NOTSET

    raise argparse.ArgumentTypeError("Invalid log level")


def __int16bits(arg):
    arg = int(arg)
    if arg < 0 or arg > 65535:
        raise argparse.ArgumentTypeError(
            "Invalid Module ID: must be between 0 and 65535")

    return arg
