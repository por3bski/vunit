# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2014-2018, Lars Asplund lars.anders.asplund@gmail.com

"""
Utilities for integrating with Vivado
"""

from __future__ import print_function
from subprocess import check_call
from os import makedirs
from os.path import abspath, join, dirname, exists, basename


def add_from_compile_order_file(vunit_obj, compile_order_file):
    """
    Add Vivado IP:s from a compile order file
    """
    compile_order, libraries, include_dirs = _read_compile_order(compile_order_file)

    # Create libraries
    for library_name in libraries:
        vunit_obj.add_library(library_name, vhdl_standard="93")

    # Add all source files to VUnit
    previous_source = None
    source_files = []
    for library_name, file_name in compile_order:
        is_verilog = file_name.endswith(".v") or file_name.endswith(".vp")

        source_file = vunit_obj.library(library_name).add_source_file(
            file_name,

            # Top level IP files are put in xil_defaultlib and can be scanned for dependencies by VUnit
            # Files in other libraries are typically encrypted and are not parsed
            no_parse=library_name != "xil_defaultlib",
            include_dirs=include_dirs if is_verilog else None)

        source_files.append(source_file)

        # Create linear dependency on Vivado IP files to match extracted compile order
        if previous_source is not None:
            source_file.add_dependency_on(previous_source)

        previous_source = source_file

    return source_files


def create_compile_order_file(project_file, compile_order_file, vivado_path=None):
    """
    Create compile file from Vivado project
    """
    print("Generating Vivado project compile order into %s ..." % abspath(compile_order_file))

    if not exists(dirname(compile_order_file)):
        makedirs(dirname(compile_order_file))

    print("Extracting compile order ...")
    run_vivado(join(dirname(__file__), "tcl", "extract_compile_order.tcl"),
               tcl_args=[project_file, compile_order_file],
               vivado_path=vivado_path)


def _read_compile_order(file_name):
    """
    Read the compile order file and filter out duplicate files
    """
    compile_order = []
    unique = set()
    include_dirs = set()
    libraries = set()

    with open(file_name, "r") as ifile:

        for line in ifile.readlines():
            library_name, file_type, file_name = line.strip().split(",", maxsplit=2)
            assert file_type in ("Verilog", "VHDL", "Verilog Header")
            libraries.add(library_name)

            # Vivado generates duplicate files for different IP:s
            # using the same underlying libraries. We remove duplicates here
            key = (library_name, basename(file_name))
            if key in unique:
                continue
            unique.add(key)

            if file_type == "Verilog Header":
                include_dirs.add(dirname(file_name))
            else:
                compile_order.append((library_name, file_name))

    return compile_order, libraries, list(include_dirs)


def run_vivado(tcl_file_name, tcl_args=None, cwd=None, vivado_path=None):
    """
    Run tcl script in Vivado in batch mode.

    Note: the shell=True is important in windows where Vivado is just a bat file.
    """
    vivado = "vivado" if vivado_path is None else join(abspath(vivado_path), "bin", "vivado")
    cmd = "{} -nojournal -nolog -notrace -mode batch -source {}".format(vivado,
                                                                        abspath(tcl_file_name))
    if tcl_args is not None:
        cmd += " -tclargs " + " ".join([str(val) for val in tcl_args])

    print(cmd)
    check_call(cmd, cwd=cwd, shell=True)
