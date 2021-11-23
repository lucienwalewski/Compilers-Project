import sys
import argparse
from enum import Enum, auto
from ssagen import crude_ssagen
from tac import Proc
from cfg import CFG, infer

class Constants(Enum):
    unused = auto()
    non_constant = auto()

def fetch_temporaries():
    '''Fetch all the temporaries in the ssa'''

def initialize_conditions(cfg: CFG):
    '''Initialise the maps Val and Ev'''
    val = {r: Constants.unused for r in fetch_temporaries(cfg)}
    ev = {b: False for b in cfg.blocks}
    return val, ev

def update_ev(cfg: CFG, ev: dict, val: dict):
    '''Update the map ev'''
    pass

def update_val(cfg: CFG, ev: dict, val: dict):
    '''Update the map val'''
    pass

def remove_instrs(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    instructions.
    '''
    pass

def remove_blocks(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    blocks.
    '''
    pass

def replace_temporary(cfg: CFG, ev: dict, val: dict):
    '''Whenever we have Val(u) = c ∈ {T,⊥}, we replace u 
    with c and delete the instruction that sets u
    '''

def optimize_sccp(decl: Proc):
    '''Perform sccp for the given declaration'''
    cfg = infer(decl)
    crude_ssagen(decl, cfg)
    val, ev = initialize_conditions(cfg)


