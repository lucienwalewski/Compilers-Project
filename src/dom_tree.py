from os import name
import os
import sys
import json
import argparse
from copy import deepcopy
from cfg import CFG, infer
from tac import load_tac, Proc


def compute_dom_tree(cfg: CFG):
    '''Given a control flow graph, compute the dominator
    tree and return the map Dom: V->P(V)'''
    dom_iter = {block: set() for block in cfg.blocks()}
    dom_iter[cfg.lab_entry] = {cfg.lab_entry}
    for v in cfg.blocks():
        if v != cfg.lab_entry:
            dom_iter[v] = set(cfg.blocks())
    while True:
        dom = deepcopy(dom_iter)
        for v in cfg.blocks():
            if v != cfg.lab_entry:
                dom_iter[v] = {v} | set.intersection(
                    *(dom[u] for u in cfg._bwd[v]))
        if dom == dom_iter:
            # # Remove itself and nodes not directly above to obtain strict dominators only
            for label in dom:
                if label in dom[label]:
                    dom[label].remove(label)
                strict_doms = set()
                for V in dom[label]:
                    if V in cfg._bwd[label]:
                        strict_doms.add(V)
                    dom[label] = strict_doms
            return dom


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
            dom = compute_dom_tree(cfg)
            print(dom)

            cfg.write_dot(fname + '.dot')
            os.system(f'dot -Tpdf -O {fname}.dot.{decl.name[1:]}.dot')
