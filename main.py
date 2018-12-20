#!/usr/bin/python3

__version__ = '0.27'

import argparse
import logging

def init_arguments():
    parser = argparse.ArgumentParser(prog='GisEditor', description='ref https://github.com/dayanuyim/GisEditor')
    parser.add_argument("-V", "--version", action="version", version=__version__)
    parser.add_argument("-v", "--verbose", action="count", default=0, help="show detail information")
    parser.add_argument("-q", "--quiet", action="count", default=0, help="decrese detail information")
    parser.add_argument("-c", "--conf", default="", help="load the config file in specific folder")
    parser.add_argument('files', nargs='*', help="Gps or photo files to parse")
    return parser.parse_args()

def set_logging(verbose=0):
    log_level = logging.DEBUG   if verbose >= 2 else \
                logging.INFO    if verbose == 1 else \
                logging.WARNING if verbose == 0 else \
                logging.ERROR
    logging.basicConfig(level=log_level,
            format="%(asctime)s.%(msecs)03d [%(levelname)s] [%(module)s] %(message)s", datefmt="%H:%M:%S")

if __name__ == '__main__':
    args = init_arguments()
    set_logging(args.verbose - args.quiet)

    # MUST init app after logging is initialized.
    import os, sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
    import app
    app.appMain(args)