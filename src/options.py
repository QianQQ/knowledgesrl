#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import probabilitymodel
import getopt
import sys

matching_algorithm = "sync_predicates"
core_args_only = True
gold_args = True
heuristic_rules = False
debug = False
bootstrap = False
probability_model = "predicate_slot"
dump = False
dump_file = ""
passive = True

options = getopt.getopt(sys.argv[1:], "d:",
    ["baseline", "fmatching-algo=", "add-non-core-args", "help",
     "model=", "bootstrap", "no-gold-args", "heuristic-rules", "dump"])

display_syntax = False
syntax_str = ("main.py [--baseline] [-d num_sample] [--fmatching-algo=algo] "
              "[--model=probability_model] [--add-non-core-args] "
              "[--bootstrap] [--no-gold-args [--heuristic-rules]] "
              "[--dump filename] [--no-passive] [--help]")

for opt,value in options[0]:
    # Removes our enhancements
    if opt == "--baseline":
        passive = False

    if opt == "-d":
        debug = True
        value = 0 if value == "" else int(value)
        if value > 0:
            n_debug = value
    if opt == "--fmatching-algo":
        matching_algorithm = value
    if opt == "--add-non-core-args":
        core_args_only = False
    if opt == "--model":
        if not value in probabilitymodel.models:
            raise Exception("Unknown model {}".format(value))
        probability_model = value
    if opt == "--bootstrap":
        bootstrap = True
    if opt == "--no-gold-args":
        gold_args = False
    if opt == "--heuristic-rules":
        heuristic_rules = True
    if opt == "--dump":
        if len(options[1]) > 0:
            dump = True
            dump_file = options[1][0]
        else:
            display_syntax = True
    if opt == "--no-passive":
        passive = False 
    if opt == "--help":
        display_syntax = True
            
if display_syntax:
    print(syntax_str)
    exit(0)
