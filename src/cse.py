from os import name
import sys
import json
import argparse
from collections import defaultdict
from typing import Generator, Iterator
from cfg import CFG, Block, infer
from tac import load_tac, Proc, Instr
from dom_tree import compute_dom_tree
from sccp import binops, unops


def expr_map_block(block: Block) -> dict:
    """Given a block, construct the mapping
    of expressions to instructions"""
    expr_map = defaultdict(set)
    for index, instr in enumerate(block.instrs()):
        if instr.opcode in binops or instr.opcode in unops:
            expr_map[(instr.opcode, instr.arg1, instr.arg2 if instr.arg2 else None)].add(index)
    return expr_map


def expr_map_cfg(cfg: CFG) -> dict:
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

def find_redefinitions(block: Block, arg: str) -> set:
    """Find the instructions indices where an argument is redefined"""
    indices = set()
    for index, instr in enumerate(block.instrs()):
        if instr.dest == arg:
            indices.add(index)
    return indices

def partition(values: list, indices: list) -> Generator:
    """Given a list of values, partition the list
    into sublists based on the list of indices. 
    This function was taken from stackoverflow"""
    idx = 0
    for index in indices:
        sublist = []
        while idx < len(values) and values[idx] < index:
            sublist.append(values[idx])
            idx += 1
        if sublist:
            yield sublist
    yield values[idx:]


def available_expr(cfg: CFG) -> dict:
    """For each block, calculate the set of instructions
    available when exiting the block"""
    avail_expr_map = {}
    for block in cfg._blockmap.values():
        avail_expr_map[block] = set()
        pass


def local_cse(block: Block):
    """Apply local cse to a single block"""
    expr_map = expr_map_block(block)
    for expr, instructions in expr_map.items():
        if len(instructions) > 1:
            instructions = sorted(list(instructions))
            redefinitions = find_redefinitions(block, expr[1])
            if expr[2]:
                redefinitions.update(find_redefinitions(block, expr[2]))
            redefinitions = sorted(list(redefinitions))
            for sublist in partition(instructions, redefinitions):
                if len(sublist) > 1:
                    for instr_idx in sublist[1:]:
                        block[instr_idx] = Instr(block[instr_idx].dest, 'copy', [block[sublist[0]].dest])
            
def global_cse(cfg: CFG):
    """Apply common subexpression elimination
    to the cfg. We first perform local cse on each block 
    before performing global cse"""

    # Perform local cse on each block
    for block in cfg._blockmap.values():
        local_cse(block)
    # Compute the dominator tree and mapping from expressions to instructions
    dom = compute_dom_tree(cfg)
    expr_map = expr_map_cfg(cfg)

    # Loop over the blocks
    for block in expr_map:
        # Loop over the blocks dominating the block
        for dom_block in dom[block]:
            pass


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
            # global_cse(cfg)
            for block in cfg._blockmap.values():
                local_cse(block)
                for instr in block.instrs():
                    print(instr)
                
            
