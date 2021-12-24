import argparse
import sys
from collections import defaultdict
from os import name
from typing import Generator

from cfg import CFG, Block, infer, linearize
from dom_tree import compute_dom_tree
from sccp import binops, unops
from tac import Instr, Proc, load_tac


def expr_map_block(block: Block) -> dict:
    """Given a block, construct the mapping
    of expressions to instructions"""
    expr_map = defaultdict(set)
    for index, instr in enumerate(block.instrs()):
        if instr.opcode in binops or instr.opcode in unops:
            expr_map[(instr.opcode, instr.arg1,
                      instr.arg2 if instr.arg2 else None)].add(index)
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
    for label, block in cfg._blockmap.items():
        avail_expr_map[label] = dict()
        for idx, instr in enumerate(block.instrs()):
            if instr.opcode in binops or instr.opcode in unops:
                if idx >= max(find_redefinitions(block, instr.dest)):
                    avail_expr_map[label][(
                        instr.opcode, instr.arg1, instr.arg2 if instr.arg2 else None)] = idx
    return avail_expr_map


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
                        block[instr_idx] = Instr(block[instr_idx].dest, 'copy', [
                                                 block[sublist[0]].dest])


def global_cse(cfg: CFG) -> CFG:
    """Apply common subexpression elimination
    to the cfg. We assume local cse has already been applied"""

    # Compute the dominator tree and mapping from expressions to instructions
    # as well as the available expressions at the end of each block
    dom = compute_dom_tree(cfg)
    expr_map = expr_map_cfg(cfg)
    avail_expr_map = available_expr(cfg)

    # Loop over the blocks
    for block in expr_map:
        # Loop over the blocks dominating the block
        for dom_block in dom[block]:
            # Loop over the expressions in the dominator block
            for dom_expr, dom_instr_idx in avail_expr_map[dom_block].items():
                # Loop over the expressions in the block
                for expr, instr_indices in expr_map[block].items():
                    # If the expressions are the same
                    if dom_expr == expr:
                        # Check for redefinitions
                        redefinitions = find_redefinitions(cfg._blockmap[block], expr[1])
                        if expr[2]:
                            redefinitions.update(find_redefinitions(cfg._blockmap[block], expr[2]))
                        # Only replace the first expression as local cse already applied
                        if not redefinitions or min(redefinitions) > min(instr_indices):
                            cfg._blockmap[block][min(instr_indices)] = Instr(cfg._blockmap[block][min(instr_indices)].dest, 'copy', [cfg._blockmap[dom_block][dom_instr_idx].dest])

def apply_cse(cfg: CFG) -> CFG:
    """Given a cfg, first apply local cse then global cse"""
    for block in cfg._blockmap.values():
        local_cse(block)
    global_cse(cfg)
    return cfg


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
            for block in cfg._blockmap.values():
                local_cse(block)
            global_cse(cfg)
            linearize(decl, cfg)
