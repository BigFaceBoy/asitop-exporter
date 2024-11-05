# This file is part of asitop, the interactive NVIDIA-GPU process viewer.
#
# Copyright 2021-2024 fangxuwei. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Prometheus exporter built on top of ``asitop``."""

from __future__ import annotations
import time
import argparse
import sys
from typing import TextIO

from prometheus_client import start_wsgi_server
from termcolor import colored

from asitop_exporter.exporter import PrometheusExporter
from asitop_exporter.utils import get_ip_address, run_powermetrics_process
from asitop_exporter.version import __version__


def cprint(text: str = '', *, file: TextIO | None = None) -> None:
    """Print colored text to a file."""
    for prefix, color in (
        ('INFO: ', 'yellow'),
        ('WARNING: ', 'yellow'),
        ('ERROR: ', 'red'),
        ('NVML ERROR: ', 'red'),
    ):
        if text.startswith(prefix):
            # text = text.replace(
            #     prefix.rstrip(),
            #     colored(prefix.rstrip(), color=color, attrs=('bold',)),
            #     1,
            # )
            text = prefix.rstrip()
    print(text, file=file)


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments for ``asitop-exporter``."""

    def posfloat(argstring: str) -> float:
        num = float(argstring)
        if num <= 0:
            raise ValueError
        return num

    posfloat.__name__ = 'positive float'

    parser = argparse.ArgumentParser(
        prog='asitop-exporter',
        description='Prometheus exporter built on top of `asitop`.',
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        '--help',
        '-h',
        dest='help',
        action='help',
        default=argparse.SUPPRESS,
        help='Show this help message and exit.',
    )
    parser.add_argument(
        '--version',
        '-V',
        dest='version',
        action='version',
        version=f'%(prog)s {__version__} (asitop {__version__})',
        help="Show %(prog)s's version number and exit.",
    )

    parser.add_argument(
        '--hostname',
        '--host',
        '-H',
        dest='hostname',
        type=str,
        default=get_ip_address(),
        metavar='HOSTNAME',
        help='Hostname to display in the exporter. (default: %(default)s)',
    )
    parser.add_argument(
        '--bind-address',
        '--bind',
        '-B',
        dest='bind_address',
        type=str,
        default='127.0.0.1',
        metavar='ADDRESS',
        help='Local address to bind to. (default: %(default)s)',
    )
    parser.add_argument(
        '--port',
        '-p',
        type=int,
        default=8000,
        help='Port to listen on. (default: %(default)d)',
    )
    parser.add_argument(
        '--interval',
        dest='interval',
        type=posfloat,
        default=5.0,
        metavar='SEC',
        help='Interval between updates in seconds. (default: %(default)s)',
    )

    parser.add_argument(
        '--post_url',
        dest='post_url',
        type=str,
        default=None,
        metavar='ADDRESS',
        help='post result to url',
    )

    parser.add_argument(
        '--alive_time',
        dest='alive_time',
        type=int,
        default=60,
        metavar='minute',
        help='powermetrics file alive time. asitop-exporter will delete the pre file and create a new one after alive_time',
    )

    args = parser.parse_args()
    if args.interval < 0.25:
        parser.error(
            f'the interval {args.interval:0.2g}s is too short, which may cause performance issues. '
            f'Expected 1/4 or higher.',
        )

    return args


def main() -> int:  # pylint: disable=too-many-locals,too-many-statements
    """Main function for ``asitop-exporter`` CLI."""
    args = parse_arguments()


    timecode = str(int(time.time()))

    # powermetrics_process = run_powermetrics_process(timecode,
    #                                                 interval=args.interval * 1000)

    exporter = PrometheusExporter(hostname=args.hostname, interval=args.interval, timecode=timecode, post_url=args.post_url, alive_time=args.alive_time)
    exporter.start_powermetrics_process()

    try:
        start_wsgi_server(port=args.port, addr=args.bind_address)
    except OSError as ex:
        if 'address already in use' in str(ex).lower():
            cprint(
                (
                    'ERROR: Address {} is already in use. '
                    'Please specify a different port via `--port <PORT>`.'
                ).format(
                    colored(
                        f'http://{args.bind_address}:{args.port}',
                        color='blue',
                        attrs=('bold', 'underline'),
                    ),
                ),
                file=sys.stderr,
            )
        elif 'cannot assign requested address' in str(ex).lower():
            cprint(
                (
                    'ERROR: Cannot assign requested address at {}. '
                    'Please specify a different address via `--bind-address <ADDRESS>`.'
                ).format(
                    colored(
                        f'http://{args.bind_address}:{args.port}',
                        color='blue',
                        attrs=('bold', 'underline'),
                    ),
                ),
                file=sys.stderr,
            )
        else:
            cprint(f'ERROR: {ex}', file=sys.stderr)
        return 1

    cprint(
        'INFO : Start the exporter on {} at {}.'.format(
            colored(args.hostname, color='magenta', attrs=('bold',)),
            colored(
                f'http://{args.bind_address}:{args.port}/metrics',
                color='green',
                attrs=('bold', 'underline'),
            ),
        ),
        file=sys.stderr,
    )

    try:
        exporter.collect()
    except KeyboardInterrupt:
        cprint(file=sys.stderr)
        cprint('INFO: Interrupted by user.', file=sys.stderr)
        exporter.terminate_powermetrics_process()

    return 0


if __name__ == '__main__':
    sys.exit(main())
