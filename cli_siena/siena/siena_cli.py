import argparse
import logging
import os
import sys
from typing import NoReturn

from siena.server.app import create_app
logger = logging.getLogger()
sys.path.insert(0,os.getcwd())

# formatter = LoggingFormatter(format_str='%(asctime)s\t%(levelname)s\t%(name)s - %(message)s')
# logging_out = logging.StreamHandler(sys.stdout)
# logging_err = logging.StreamHandler(sys.stderr)
# logging_out.setFormatter(formatter)
# logging_err.setFormatter(formatter)
# logging_out.addFilter(MaxLevelFilter(logging.WARNING))
# logging_out.setLevel(logging.DEBUG)
# logging_err.setLevel(logging.WARNING)
# logger.addHandler(logging_out)
# logger.addHandler(logging_err)
# logger.setLevel(level=logging.INFO)

# disabling unwanted tf cuda logs
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


def create_argument_parser():
    """
    Parses the arguments passed to SIENA through SIENA CLI tool.
    Returns:
        argparse.ArgumentParser()
    """

    parser = argparse.ArgumentParser(prog="siena", description="starts SIENA CLI")
    subparsers = parser.add_subparsers(help='desired SIENA interface to run [cli/server]', dest="subparser_name")

    parser_server = subparsers.add_parser(
        name="server",
        help='run SIENA server, a web-based visualization tool for SIENA.'
    )
    parser_server.add_argument(
        "-p",
        "--port",
        type=int,
        default=None,
        help="the port to start the siena server at.",
    )
    parser_server.add_argument(
        "-d",
        "--debug",
        type=str,
        choices=["True", "False", "true", "false", "T", "t", "F", "f", "1", "0"],
        default="True",
        help="debug mode of the server.",
    )

    return parser


def run_siena_cli() -> NoReturn:
    logger.info("Running main SIENA CLI.")
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()
    interface = cmdline_args.subparser_name

    if not interface:
        arg_parser.print_help()
        logger.error("Please specify a valid positional arg out of \'explain\', \'visualize\', "
                     "\'server\', \'init\' to use SIENA CLI.")
        return

    if str(interface).lower() == "server":
        server_port = cmdline_args.port
        debug_mode = cmdline_args.debug

        # configs = get_default_configs(interface=InterfaceType.INTERFACE_SERVER)

        # if not configs:
        #     logger.error("Failed to retrieve default SIENA configs. SIENA CLI will be terminated.")
        #     return
        app = create_app()
        app.run(port=server_port)

    else:
        logger.error('One or more incorrect CLI arguments detected. Refer "siena -h" to view allowed arguments')
        return


if __name__ == '__main__':
    logger.error("This script cannot be directly executed. please use the 'siena' CLI instead.")
    exit(1)