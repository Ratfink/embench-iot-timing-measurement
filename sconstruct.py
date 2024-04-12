#!/usr/bin/env python3

# Script to build all benchmarks

# Copyright (C) 2017, 2024 Embecosm Limited
#
# Contributor: Konrad Moron <konrad.moron@tum.de>
#
# This file is part of Embench.

# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
import os

def find_benchmarks(bd, env):
    dir_iter = Path('src').iterdir()
    return ([bench for bench in dir_iter if bench.is_dir()] + [env['dummy_benchmark']])

def parse_options():
    num_cpu = int(os.environ.get('NUM_CPU', 2))
    SetOption('num_jobs', num_cpu)
    AddOption('--build-dir', nargs=1, type='string', default='bd')
    AddOption('--config-dir', nargs=1, type='string', default='config2')
    config_dir = Path(GetOption('config_dir')).absolute()
    bd = Path(GetOption('build_dir')).absolute()

    vars = Variables(None, ARGUMENTS)
    print(ARGUMENTS)
    vars.Add('cc', default=env['CC'])
    vars.Add('cflags', default=env['CCFLAGS'])
    vars.Add('ld', default=env['LINK'])
    vars.Add('ldflags', default=env['LINKFLAGS'])
    vars.Add('user_libs', default=[])
    vars.Add('warmup_heat', default=1)
    vars.Add('cpu_mhz', default=1)
    vars.Add('dummy_benchmark', default=(bd / 'support/dummy-benchmark'))
    return vars

def setup_directories(bd, config_dir):
    VariantDir(bd / "src", "src")
    VariantDir(bd / "support", "support")
    VariantDir(bd / "config", config_dir)
    SConsignFile(bd / ".sconsign.dblite")

def populate_build_env(env, vars):
    vars.Update(env)
    env.Append(CPPDEFINES={ 'WARMUP_HEAT' : '${warmup_heat}',
                            'CPU_MHZ' :     '${cpu_mhz}'})
    env.Append(CPPPATH=[bd / 'support', config_dir])
    env.Replace(CCFLAGS = "${cflags}")
    env.Replace(LINKFLAGS = "${ldflags}")
    env.Replace(CC = "${cc}")
    env.Replace(LINK = "${ld}")
    env.Prepend(LIBS = "${user_libs}")

def build_support_objects(env):
    support_objects = []
    support_objects += env.Object(str(bd / 'support/main.c'))
    support_objects += env.Object(str(bd / 'support/beebsc.c'))
    support_objects += env.Object(str(bd / 'config/boardsupport.c'))
    env.Default(support_objects)
    return support_objects


# MAIN BUILD SCRIPT
env = DefaultEnvironment()
vars = parse_options()

bd = Path(GetOption('build_dir')).absolute()
config_dir = Path(GetOption('config_dir')).absolute()

setup_directories(bd, config_dir)
env.Replace(BUILD_DIR=bd)
env.Replace(CONFIG_DIR=config_dir)
populate_build_env(env, vars)

# Setup Help Text
env.Help("\nCustomizable Variables:", append=True)
env.Help(vars.GenerateHelpText(env), append=True)
Export('env')

support_objects = build_support_objects(env)
benchmark_paths = find_benchmarks(bd, env)

benchmark_objects = {
    (bd / bench / bench.name): 
        (env.Object(Glob(str(bd / bench / "*.c")))
            if not (bd / bench / "sconscript.py").is_file()
            else SConscript(bd / bench / "sconscript.py"))
    for bench in benchmark_paths
}
env.Default(benchmark_objects.values())

for benchname, objects in benchmark_objects.items():
    bench_exe = env.Program(str(benchname), objects + support_objects)
    env.Default(bench_exe)
