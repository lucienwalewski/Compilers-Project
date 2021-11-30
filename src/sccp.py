import sys
import argparse
from enum import Enum, auto
from ssagen import crude_ssagen
from tac import Proc, Instr
from cfg import CFG, infer, Block
from tac import *
import json



from typing import List, Union

import copy


class Constants(Enum):
    unused = auto()
    non_constant = auto()


def fetch_temporaries(cfg: CFG):
    '''Fetch all the temporaries in the ssa'''
    temps = set()
    for label, block in cfg._blockmap.items():
        for instruction in block.instrs():
            if instruction.opcode != "phi" :
                for temp in instruction.uses():
                    temps.add(temp)
            else :
                for temp in instruction.uses() :
                    temps.add(temp[1])
                
                
            temps.add(instruction.dest)
            
    return list(temps)


def initialize_conditions(cfg: CFG):
    '''Initialise the maps Val and Ev'''
    val = {v: Constants.unused for v in fetch_temporaries(cfg)}
    ev = {label: (True if label == cfg.lab_entry else False)
          for label in cfg._blockmap}
    return ev, val


def check_jmp_condition(jmp_type: str, value: int):
    if jmp_type == "jz":
        return value == 0
    elif jmp_type == "jnz":
        return value != 0
    elif jmp_type == "jl":
        return value < 0
    elif jmp_type == "jle":
        return value <= 0
    elif jmp_type == "jnl":
        return value >= 0
    elif jmp_type == "jnle":
        return value > 0


def update_ev(cfg: CFG, ev: dict, val: dict) -> bool:
    '''Update the map ev and return true if any modifications 
    are made'''
    modified = False
    for block, executed in ev.items():
        definite_jmp = False  # Set to true when a definite jump is found
        if executed:
            for jmp in cfg._blockmap[block].reversed_jumps():
                jmp_type = jmp.opcode

                if jmp_type == "jmp" and not definite_jmp:
                    dest_block = jmp.arg1
                    modified |= update_dict(ev, dest_block, True)
                else:
                    value = val[jmp.arg1]
                    dest_block = jmp.arg2
                    if value is Constants.non_constant:
                        modified |= update_dict(ev, dest_block, True)
                    elif value is Constants.unused:
                        break  # Stop further updates to this block
                    else:  # Definite jump found
                        if check_jmp_condition(jmp_type, value):
                            modified |= update_dict(ev, dest_block, True)
                            definite_jmp = True
                        else:
                            # FIXME: This may not be correct
                            pass
    return modified


def update_dict(d: dict, key: str, val: Union[str, Constants, bool]):
    '''Make an update to the dictionaries ev or val and return true
    if the dictionary was modified'''
    old_value = d[key]
    d[key] = val
    return old_value != val


def update_dest(instr: Instr, dest: str, val: dict):
    '''Make an update to the dictionary val based on the instruction
    and return true if the dictionary was modified'''
    old_value = val[dest]
    if instr.arg2:
        val[dest] = eval(str(instr.ag1) + instr.opcode + str(instr.arg2))
    else:
        val[dest] = eval(instr.opcode + str(instr.arg1))
    return old_value != val[dest]


def update_val(cfg: CFG, ev: dict, val: dict) -> bool:
    '''Update the map val and return true if any modifications
    are made'''
    consts = {Constants.unused, Constants.non_constant}
    modified = False
    for block, executed in ev.items():
        if executed:
            for instr in cfg._blockmap[block].instrs():
                dest = instr.dest
                opcode = instr.opcode
                if opcode == 'phi':
                    for i, (label_i, temporary_i) in enumerate(instr.uses()):
                        if val[temporary_i] not in val[dest] | consts and val[dest] not in consts:
                            modified |= update_dict(
                                val, dest, Constants.non_constant)
                        elif val[temporary_i] is Constants.non_constant and ev[label_i]:
                            modified |= update_dict(
                                val, dest, Constants.non_constant)
                        elif val[temporary_i] not in consts:
                            condition = True
                            for j, (label_j, temporary_j) in enumerate(instr.uses()):
                                if i != j:
                                    if val[temporary_j] is Constants.unused or not ev[label_j] or val[temporary_j] == val[temporary_i]:
                                        continue
                                    else:
                                        condition = False
                            if condition:
                                modified |= update_dict(
                                    val, dest, val[temporary_i])
                else:
                    if all(val[arg] not in {Constants.non_constant, Constants.unused} for arg in instr.uses()):
                        modified |= update_dest(instr, dest, val)
                    elif any(val[arg] is Constants.non_constant for arg in instr.uses()):
                        modified |= update_dict(
                            val, dest, Constants.non_constant)


def remove_instrs(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    instructions.
    '''
    new_blocks = []
    
    for label,block in cfg._blockmap.items() :
        
        
        new_body = []
        for instr in block.body :
            unused_temp = False
            uses = [instr.dest] + [(use if len(use)==1 else use[1]) for use in instr.uses() ]
            for use in uses :
                if val[use] == Constants.unused :
                    unused_temp = True
            if not unused_temp : new_body.append(instr)
            
        new_blocks.append(Block(label,new_body,block.jumps))
        
    return CFG(cfg.proc_name, cfg.lab_entry, new_blocks)

        
    
        
        
                
                    
            
    


def remove_blocks(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    blocks.
    '''
    new_blocks = []
    for lab in cfg._blockmap :
        if ev[lab] :
            new_blocks.append(cfg._blockmap[lab])
 
    return CFG(cfg.proc_name, cfg.lab_entry, new_blocks)
        
    


def replace_temporary(cfg: CFG, ev: dict, val: dict):
    '''Whenever we have Val(u) = c ∈ {T,⊥}, we replace u 
    with c and delete the instruction that sets u 
    '''
    
    # Replace i with c :
    
    not_consts = {Constants.unused, Constants.non_constant}

    for block in cfg._blockmap :
        for instr in block.body :
            if val[instr.dest] not in not_consts :
                    instr.dest = val[instr.dest]
            if instr.opcode != "phi" :
                if val[instr.arg1] not in not_consts :
                    instr.arg1 = val[instr.arg1]
                if val[instr.arg2] not in not_consts :
                        instr.arg2 = val[instr.arg2]
            else :
                # FIXME: Handle phi function case 
                
    # FIXME: delete the instruction that sets u :
    
    
                
                
                
                
                
        

        
    


def optimize_sccp(decl: Proc):
    '''Perform sccp for the given declaration'''
    cfg = infer(decl)
    crude_ssagen(decl, cfg)
    ev, val = initialize_conditions(cfg)
    modified = True
    while modified:
        modified = False
        modified |= update_ev(cfg, ev, val)
        modified |= update_val(cfg, ev, val)
    cfg = remove_blocks(cfg, ev, val)
    cfg = remove_instrs(cfg, ev, val)


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
