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
    ev = {b.label: (True if b.label == cfg.lab_entry else False)  for b in cfg._blockmap}
    return ev, val

def update_ev(cfg: CFG, ev: dict, val: dict):
    '''Update the map ev'''
    change = False
    for label, block in cfg._blockmap :
        definite_jump = False 
        for jump in block.jumps :
            jump_type = jump.opcode
            if  jump_type == "jmp" and not definite_jump:
                ev["label"] = True 
            else :
                x = jump.arg1 :
                if val[x] == Constants.non_constant :
                    ev["label"] = True 
                if val[x] == Constants.unused :
                    ev["label"] = True 
                else :
                    ## check according to type of jump and value of the temporary
                    definite_jump = True 



    return change 

def update_val(cfg: CFG, ev: dict, val: dict):
    '''Update the map val'''
    change = False
    return change

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
    ev, val = initialize_conditions(cfg)
    while max(update_ev(cfg,ev,val), update_val(cfg,ev,val)) :
        pass
    
        


