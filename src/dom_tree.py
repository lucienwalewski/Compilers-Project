import sys
import json
import argparse
from cfg import CFG


def compute_dom_tree(cfg: CFG):
    '''Given a control flow graph, compute the dominator
    tree and return the map Dom: V->P(V)'''
    dom_iter = {block: set() for block in cfg.blocks}
    dom_iter[cfg.lab_entry] = {cfg.lab_entry}
    for v in cfg.blocks:
        if v != cfg.lab_entry:
            dom_iter[v] = set(cfg.blocks)
    while True:
        dom = dom_iter
        for v in cfg.blocks:
            if v != cfg.lab_entry:
                dom_iter[v].update(set.intersection(dom[u] for u in cfg._bwd[v]))
        if dom == dom_iter:
            return dom
