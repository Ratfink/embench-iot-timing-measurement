#!/usr/bin/env python3

# Python module to run programs on a stm32f4-discovery board

# Copyright (C) 2019 Embecosm Limited
#
# Contributor: Jeremy Bennett <jeremy.bennett@embecosm.com>
#
# This file is part of Embench.

# SPDX-License-Identifier: GPL-3.0-or-later

"""
Embench module to run benchmark programs.

This version is suitable for a gdbserver with simulator.
"""

import argparse
import subprocess
import re

from embench_core import log

cpu_mhz = 1

def get_target_args(remnant):
    """Parse left over arguments"""
    parser = argparse.ArgumentParser(description='Get target specific args')

    parser.add_argument(
        '--gdb-command',
        type=str,
        default='gdb',
        help='Command to invoke GDB',
    )
    parser.add_argument(
        '--gdb-data-directory',
        type=str,
        default='',
        help='Data directory for GDB',
    )
    parser.add_argument(
        '--gdbserver-command',
        type=str,
        default='gdbserver',
        help='Command to invoke the GDB server',
    )
    parser.add_argument(
        '--cpu-mhz',
        type=int,
        default=1,
        help='Processor clock speed in MHz'
    )
    parser.add_argument(
        '--benchmark-iters',
        type=int,
        default=10,
        help='Number of iterations to run the benchmark'
    )
    parser.add_argument(
        '--output-filename',
        type=str,
        default='',
        help='Filename to store timing results to, in a JSON format'
    )
    parser.add_argument(
        '--output-opts',
        type=str,
        default='nothing',
        help='Extra options to store in the output file'
    )

    return parser.parse_args(remnant)


def build_benchmark_cmd(path, args):
    """Construct the command to run the benchmark.  "args" is a
       namespace with target specific arguments"""
    global cpu_mhz
    cpu_mhz = args.cpu_mhz

    cmd = [f'{args.gdb_command}']
    if args.gdb_data_directory:
        cmd.append(f'--data-directory={args.gdb_data_directory}')
    if args.output_filename == '':
        args.output_filename = f'{path.split('/')[-1]}.json'
    log.info(f'Saving to {args.output_filename}')
    gdb_comms = [
        'set confirm off',
        f'file {path}',
        'target extended-remote :3333',
        'load',
        f'time-function {args.benchmark_iters} {args.output_filename} {args.output_opts}',
        'quit',
    ]

    for arg in gdb_comms:
        cmd.extend(['-ex', arg])

    return cmd


def decode_results(stdout_str, stderr_str):
    """Extract the results from the output string of the run. Return the
       elapsed time in milliseconds or zero if the run failed."""
    # Return code is in standard output. We look for the string that means we
    # hit a breakpoint on _exit, then for the string returning the value.
    print(stdout_str)
    rcstr = re.search(
        'Breakpoint 3,.*\$3 = (\d+)', stdout_str, re.S
    )
    if not rcstr:
        log.debug('Warning: Failed to find return code')
        return 0.0
    if int(rcstr.group(1)) != 0:
        log.debug('Warning: Error return code')

    # The start and end cycle counts are in the stderr string
    starttime = re.search('\$1 = (\d+)', stdout_str, re.S)
    endtime = re.search('\$2 = (\d+)', stdout_str, re.S)
    if not starttime or not endtime:
        log.debug('Warning: Failed to find timing')
        return 0.0

    # Time from cycles to milliseconds
    global cpu_mhz
    return (int(endtime.group(1)) - int(starttime.group(1))) / cpu_mhz / 1000.0

def run_benchmark(bench, path, args):
    """Runs the benchmark "bench" at "path". "args" is a namespace
       with target specific arguments. This function will be called
       in parallel unless if the number of tasks is limited via
       command line. "run_benchmark" should return the result in
       milliseconds.
    """
    arglist = build_benchmark_cmd(path, args)
    try:
        res = subprocess.run(
            arglist,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        log.warning(f'Warning: Run of {bench} timed out.')
        return None
    if res.returncode != 0:
        return None
    return decode_results(res.stdout.decode('utf-8'), res.stderr.decode('utf-8'))
