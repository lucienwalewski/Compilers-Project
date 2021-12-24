from os import name
import sys
import json
import argparse
from collections import defaultdict
from cfg import CFG, Block, infer
from tac import load_tac, Proc, Instr
from dom_tree import compute_dom_tree
from sccp import binops, unops




def replace_operation(block, dominating_block, instr, duplicate_instr):
    """Replace the operation with a copy"""
    pass

def expr_map_block(block: Block):
    """Given a block, construct the mapping
    of expressions to instructions"""
    expr_map = defaultdict(set)
    for index, instr in enumerate(block.instrs()):
        if instr.opcode in binops or instr.opcode in unops:
            expr_map[(instr.opcode, instr.arg1, instr.arg2 if instr.arg2 else None)].add(index)
    return expr_map


def expr_map_cfg(cfg: CFG):
    """Given a cfg, construct the mapping of expressions for
    each block"""
    expressions = {}
    for label, block in cfg._blockmap.items():
        expressions[label] = defaultdict(set)
        for index, instr in enumerate(block.instrs()):
            if instr.opcode in binops or instr.opcode in unops:
                expressions[label][(
                    instr.opcode, instr.arg1, instr.arg2 if instr.arg2 else None)].add(index)
    return expressions

def find_redefinitions(block: Block, arg: str):
    """Find the instructions indices where an argument is redefined"""
    indices = []
    for index, instr in enumerate(block.instrs()):
        if instr.dest == arg:
            indices.append(index)
    return indices


def local_cse(block: Block):
    """Apply local cse to a single block"""
    expr_map = expr_map_block(block)
    for expr, instructions in expr_map.items():
        if len(instructions) > 1:
            instructions = sorted(list(instructions))
            redefinitions1 = find_redefinitions(block, expr[1])
            if expr[2]:
                redefinitions2 = find_redefinitions(block, expr[2])
            # FIXME:
            # Given the instruction indices and the redefinition indices, 
            # compute which instructions can be replaced
     




def global_cse(cfg: CFG):
    """Apply common subexpression elimination
    to the cfg"""

    # First compute the domintor tree
    dom = compute_dom_tree(cfg)
    print(dom)
    # expressions = expr_map_cfg(cfg)

    # # First replace duplicate expressions within the same block
    # # Loop over the blocks
    # for block in expressions:
    # # Loop over the blocks dominating the block
    # for dominating_block in dom[block]:
    #     # Look over the expressions in the dominating block
    #     for dom_expr in expressions[dominating_block]:
    #         # Loop over the expr in the block
    #         for dupl_expr in expressions[block]:
    #             # Check if it is indeed a duplicate
    #             if dupl_expr == dom_expr:
    #                 print(block, dominating_block, dom_expr, dupl_expr)
    #                 print(expressions[dominating_block])
    #                 # Fetch instructions
    #                 dom_instr = cfg._blockmap[dominating_block][expressions[dominating_block][dom_expr]]
    #                 dupl_instr = cfg._blockmap[block][expressions[block][dupl_expr]]
    #                 # Replace the instruction with a copy
    #                 new_instr = Instr(
    #                     dupl_instr.dest, 'copy', dom_instr.dest)
    #                 cfg._blockmap[block][expressions[block]
    #                                      [dupl_expr]] = new_instr


if __name__ == "__main__":
    # Parse the command line arguments
    ap = argparse.ArgumentParser(
        description='Control flow optimization. TAC->TAC')
    ap.add_argument('fname', metavar='FILE', type=str, nargs=1,
                    help='The BX(JSON) file to process')
    ap.add_argument('-o', '--output', dest='output', type=str)
    opts = ap.parse_args(sys.argv[1:])
    fname = opts.fname[0]

    # Read the input file into tac
    try:
        tac_list = load_tac(fname)
    except ValueError as e:
        print(e)
        sys.exit(1)

    for count, decl in enumerate(tac_list):
        if isinstance(decl, Proc):
            cfg = infer(decl)
