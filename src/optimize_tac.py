"""Final deliverable. Takes a tac file 
and produces the optimized tac in ssa form.

Use:
    bx2tac_opt.py <tac-file>.tac.json

    <tac-file>: a tac file to be optimized

Returns:
    <bx-file>_optimised.tac.json: a TAC file
"""

import sys
import argparse
import json
from cfg import infer, linearize
from ssagen import crude_ssagen
from tac import Proc, load_tac
from sccp import optimize_sccp
from ssa_min import minimize
from cse import apply_cse
from tac_doft import GCP

if __name__ == "__main__":
    # Parse the command line arguments
    ap = argparse.ArgumentParser(
        description='Control flow optimization. TAC->TAC')
    ap.add_argument('fname', metavar='FILE', type=str, nargs=1,
                    help='The BX(JSON) file to process')
    ap.add_argument('-o', '--output', dest='output', type=str)
    ap.add_argument('-p', action='store_true', dest='print_cfg')
    opts = ap.parse_args(sys.argv[1:])
    fname = opts.fname[0]

    # Read the input file into tac
    try:
        tac_list = load_tac(fname)
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Optimize the declarations
    new_tac_list = []
    for decl in tac_list:
        if isinstance(decl, Proc):
            cfg = infer(decl)
            crude_ssagen(decl, cfg)
            cfg = minimize(cfg)
            cfg = optimize_sccp(cfg)
            cfg = apply_cse(cfg)
            cfg = GCP(cfg)
            linearize(decl, cfg)
            new_tac_list.append(decl)

    # Write the output file if requested
    if opts.output:
        with open(opts.output, 'w') as f:
            json.dump([decl.js_obj for decl in new_tac_list], f)

    # Print to console if requested
    if opts.print_cfg:
        for decl in new_tac_list:
            print(decl)
