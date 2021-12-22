"""Final deliverable. Takes a bx file 
and produces the optimized TAC in SSA form.

Use:
    bx2tac_opt.py <bx-file>.bx

    bx-file: a bx file to be converted to TAC

Returns:
    <bx-file>.tac: a TAC file
"""

import sys
import argparse
from tac import Proc
from sccp import optimize_sccp
import tac




if __name__ == '__main__':


    parser = argparse.ArgumentParser(
        description='Control flow optimization. bx->tac (ssa form)')
    parser.add_argument('bx_file', metavar='FILE', type=str, nargs=1,
                    help='The bx file to be converted to tac')
    parser.add_argument('-o', '--output', dest='output', type=str)
    args = parser.parse_args(sys.argv[1:])
    bx_file = args.bx_file[0]

    # Lex and parse the input file
    # FIXME
    tac_list = []

    # Once in tac form, perform sccp
    new_tac_list = []
    print("yo")
    for decl in tac_list:
        print(decl)
        if isinstance(decl, Proc):
            print("test")
            optimize_sccp(decl)
        new_tac_list.append(decl)