import logging

from .initialization import _set_parser, _set_logging
from .tasks import start_tasks


def main(raw_args=None):
    parser = _set_parser()

    args = parser.parse_args(raw_args)
    _set_logging(args.loglevel)

    logging.info(f"Device: {args.device} Baud: {args.baudrate} Port: {args.port}")

    start_tasks(args)


if __name__ == "__main__":
    main()
