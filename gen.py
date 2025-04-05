#!/usr/bin/env python3

import shutil
from argparse import ArgumentParser

from oresat_configs import gen_cand_files, gen_cand_od_config, gen_dbc_node

OD_CONFIG_PATH = "od.yaml"
GEN_DIR_PATH = "oresat_star_tracker/gen"

parser = ArgumentParser()
parser.add_argument("gen", nargs="?", choices=["code", "config", "dbc", "clean"], default="code")
args = parser.parse_args()

if args.gen == "code":
    gen_cand_files(OD_CONFIG_PATH, GEN_DIR_PATH)
if args.gen == "config":
    gen_cand_od_config(OD_CONFIG_PATH)
elif args.gen == "dbc":
    gen_dbc_node(OD_CONFIG_PATH, node_id=0x34)
elif args.gen == "clean":
    shutil.rmtree(GEN_DIR_PATH, ignore_errors=True)
