import argparse
import logging
import os
import sys
from typing import NoReturn

from siena.server.siena_server import SIENAServer
from siena.shared.constants import (
    LoggingLevel,
    InterfaceType,
    DEFAULT_SERVER_PORT,
    DEFAULT_SERVER_HOST,
)
from siena.utils.siena_logging_formatter import (
    SIENALoggingFormatter,
    MaxLevelFilter,
)

logger = logging.getLogger()
sys.path.insert(0, os.getcwd())

formatter = SIENALoggingFormatter(format_str='%(asctime)s\t%(levelname)s\t%(name)s - %(message)s')
logging_out = logging.StreamHandler(sys.stdout)
logging_err = logging.StreamHandler(sys.stderr)
logging_out.setFormatter(formatter)
logging_err.setFormatter(formatter)
logging_out.addFilter(MaxLevelFilter(logging.WARNING))
logging_out.setLevel(logging.DEBUG)
logging_err.setLevel(logging.WARNING)
logger.addHandler(logging_out)
logger.addHandler(logging_err)
logger.setLevel(level=logging.INFO)


def create_argument_parser():
    """
    Parses the arguments passed to SIENA through SIENA CLI tool.
    Returns:
        argparse.ArgumentParser()
    """

    parser = argparse.ArgumentParser(
        prog="siena",
        description="starts SIENA CLI"
    )
    subparsers = parser.add_subparsers(
        help='desired SIENA interface to run [cli/server]',
        dest="subparser_name"
    )

    parser_server = subparsers.add_parser(
        name="server",
        help='run SIENA server, a web-based visualization '
             'tool for SIENA.'
    )
    parser_server.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="the port to start the siena server at.",
    )
    parser_server.add_argument(
        "--debug",
        action="store_true",
        help="sets the logging level to debug mode from "
             "info and flask server debug mode to true.",
    )

    return parser


def _set_logging_level(level: LoggingLevel = LoggingLevel.INFO) -> NoReturn:
    """Sets logging level of SIENA"""

    if level == LoggingLevel.NOTSET:
        logger.setLevel(level=logging.NOTSET)
    elif level == LoggingLevel.DEBUG:
        logger.setLevel(level=logging.DEBUG)
    elif level == LoggingLevel.INFO:
        logger.setLevel(level=logging.INFO)
    elif level == LoggingLevel.WARNING:
        logger.setLevel(level=logging.WARNING)
    elif level == LoggingLevel.ERROR:
        logger.setLevel(level=logging.ERROR)
    elif level == LoggingLevel.CRITICAL:
        logger.setLevel(level=logging.CRITICAL)
    elif level == LoggingLevel.QUIET:
        logging.disable(level=logging.CRITICAL)
    else:
        logger.setLevel(level=logging.INFO)


def run_siena_cli() -> NoReturn:
    logger.info("Running main SIENA CLI.")
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()
    interface = cmdline_args.subparser_name

    if not interface:
        arg_parser.print_help()
        logger.error("Please specify a valid positional arg "
                     "out of [\'server\'] to use SIENA CLI.")
        return

    try:
        if str(interface).lower() == InterfaceType.INTERFACE_SERVER:
            server_port = cmdline_args.port
            debug_mode = cmdline_args.debug
            if debug_mode:
                _set_logging_level(level=LoggingLevel.DEBUG)
            else:
                _set_logging_level(level=LoggingLevel.INFO)

            configs = {
                "server_port": server_port or DEFAULT_SERVER_PORT,
                "server_host": DEFAULT_SERVER_HOST
            }
            siena_server = SIENAServer(
                configs=configs,
                debug_mode=debug_mode,
            )
            siena_server.run()

        else:
            logger.error('One or more incorrect CLI arguments detected. '
                         'Refer "siena -h" to view allowed arguments')
            return
    except KeyboardInterrupt:
        logger.info(f"Gracefully terminating SIENA CLI...")


if __name__ == '__main__':
    logger.error("This script cannot be directly executed. "
                 "please use the 'SIENA CLI' instead.")
    exit(1)
