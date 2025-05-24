#!/usr/bin/env python3

import shutil
from argparse import ArgumentParser

from oresat_configs import gen_cand_files, gen_dbc_node

OD_CONFIG_PATH = "od.yaml"
GEN_DIR_PATH = "oresat_star_tracker/gen"

parser = ArgumentParser()
subparsers = parser.add_subparsers(dest="subcommand")

subparser = subparsers.add_parser("code", help="generate code for project")

subparser = subparsers.add_parser("dbc", help="generate dbc file")
subparser.add_argument("-n", "--node-id", default=0x7C)

subparser = subparsers.add_parser("clean", help="clean up generated code")

args = parser.parse_args()

if args.subcommand in ("code", None):
    gen_cand_files(OD_CONFIG_PATH, GEN_DIR_PATH)
elif args.subcommand == "dbc":
    gen_dbc_node(OD_CONFIG_PATH, node_id=args.node_id)
elif args.subcommand == "clean":
    shutil.rmtree(GEN_DIR_PATH, ignore_errors=True)
