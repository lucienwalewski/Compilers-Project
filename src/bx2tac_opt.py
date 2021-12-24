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
from tac_doft import optimize_decl
import tac
from parser import *
from lexer import *
import bx_ast as ast
import bx2tac
import json



if __name__ == '__main__':


    parser = argparse.ArgumentParser(
        description='Control flow optimization. bx->tac (ssa form)')
    parser.add_argument('bx_file', metavar='FILE', type=str, nargs=1,
                    help='The bx file to be converted to tac')
    parser.add_argument('-o', '--output', dest='output', type=str)
    args = parser.parse_args(sys.argv[1:])
    bx_file = args.bx_file[0]
    tac_file = bx_file + 'tac.json'

    # Lex and parse the input file
    with open(bx_file, 'r') as fp:
        data = fp.read()
        AST = parser.parse(data, lexer=lexer)
        assert AST is not None
        AST.type_check()
        tac_list = TACGen(AST.declarations).ship()

    # Once in tac form, perform sccp + copy propagation
    new_tac_list = []
    print("yo")
    for decl in tac_list:
        print(decl)
        if isinstance(decl, Proc):
            print("test")
            optimize_sccp(decl)
            optimize_decl(decl)
        new_tac_list.append(decl)