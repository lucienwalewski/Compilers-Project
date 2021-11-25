import sys
import argparse
from enum import Enum, auto
from ssagen import crude_ssagen
from tac import Proc
from cfg import CFG, infer


from typing import List, Union

from cfg import *
from ssagen import *
from tac import *
import copy


class Constants(Enum):
    unused = auto()
    non_constant = auto()

def fetch_temporaries(cfg: CFG):
    '''Fetch all the temporaries in the ssa'''
    temps = set()
    for label, block in cfg._blockmap.items() :
        for instruction in block.instrs() :
            for temp in instruction.uses :
                temps.add(temp)
            temp.add(instruction.dest)
    return list(temps)


def initialize_conditions(cfg: CFG):
    '''Initialise the maps Val and Ev'''
    val = {r: Constants.unused for r in fetch_temporaries(cfg)}
    ev = {label: (True if label == cfg.lab_entry else False)  for label, _ in cfg._blockmap.items()}
    return ev, val

def update_ev(cfg: CFG, ev: dict, val: dict):
    '''Update the map ev'''
    change = False
    for label, block in cfg._blockmap.items() :
        definite_jump = False 
        for jump in block.jumps :
            jump_type = jump.opcode
            value = val[x]


            if  jump_type == "jmp" and not definite_jump:
                ev["label"] = True 
            
            else :
                x = jump.arg1 
                if value == Constants.non_constant :
                    ev["label"] = True 
                if value == Constants.unused :
                    ev["label"] = True 

                else :
                    if jump_type == "jz" :
                        if value == 0 :
                            ev["label"] = True 
                            definite_jump = True

                    elif jump_type == "jnz" :
                        if value != 0 :
                            ev["label"] = True 
                            definite_jump = True

                    elif jump_type == "jl" :
                        if value < 0 :
                            ev["label"] = True 
                            definite_jump = True
                        
                    elif jump_type == "jle" :
                        if value <= 0 :
                            ev["label"] = True 
                            definite_jump = True  

                    elif jump_type == "jnl" :
                        if value >= 0 :
                            ev["label"] = True 
                            definite_jump = True

                    elif jump_type == "jnle" :
                        if value > 0 :
                            ev["label"] = True 
                            definite_jump = True

    return change 

def update_val(cfg: CFG, ev: dict, val: dict):
    '''Update the map val'''
    no_value = [Constants.unused, Constants,non_constant] 
    change = False
    for label, block in cfg._blockmap.items() :
        if ev[label] :
            for instruction in block.instrs() :
                    dest = instruction.dest 
                    arg1, arg2 = instruction.arg1, instruction.arg2
                    opcode = instruction.opcode 
                    if opcode != "phi" :
                        if val[arg1] not in no_value and (not arg2 or val[arg2] not in no_value) :
                            val[dest] = val[arg1] + val[arg2]
                        elif (arg1 and val[arg1]==Constants.non_constant) or (arg2 and val[arg2]==Constants.non_constant) :
                            val[dest] = Constants.non_constant

                    else :
                        values = {ev[label_block]:val[temp] for label_block,temp in instruction.uses}
                        if (True,Constants.non_constant) in values.items() :
                            var[dest] = Constants.non_constant
                        else :
                            change_phi = False
                            for (label_block,temp) in values :
                                if not change_phi : 
                                    if var[temp] not in no_value :

                                        for (label_block2,temp2) in values :
                                            if var[temp2] not in no_value and var[temp2] != var[temp] :
                                                var[dest]=Constants.non_constant
                                                change_phi = True
                                        
                                        if False not in [(temp2==temp or var[temp2]==var[temp] or not ev[label_block2]) for label_block2,temp2 in instruction.uses] :
                                            var[dest] = var[temp]
                                            change_phi = True

                                    
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
    print(ev)
    print(val)


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
    # Optimize the declarations
    new_tac_list = []
    for decl in tac_list:
        if isinstance(decl, Proc):
            optimize_sccp(decl)
        new_tac_list.append(decl)

    # Write the output file if requested
    if opts.output:
        with open(opts.output, 'w') as f:
            json.dump([decl.js_obj for decl in new_tac_list], f)
    # Execute the program
    else:
        execute(new_tac_list)

        # cfg.write_dot(fname + '.dot')
        # os.system(f'dot -Tpdf -O {fname}.dot.{tac_unit.name[1:]}.dot')
    
        


