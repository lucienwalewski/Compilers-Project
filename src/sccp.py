import sys
import argparse
from enum import Enum, auto
from ssagen import crude_ssagen
from tac import Proc, Instr
from cfg import CFG, infer


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
            for temp in instruction.uses:
                temps.add(temp)
            temp.add(instruction.dest)
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

def update_ev(cfg: CFG, ev: dict[str, bool], val: dict) -> bool:
    '''Update the map ev and return true if any modifications 
    are made'''
    modified = False
    for block, executed in ev.items():
        definite_jmp = False  # Set to true when a definite jump is found
        if executed:
            for jmp in cfg._blockmap[block].reversed_jumps():
                jmp_type = jmp.opcode
                value = val[jmp.arg1]
                dest_block = jmp.arg2
                if jmp_type == "jmp" and not definite_jmp:
                    ev[dest_block] = True
                    modified = True
                else:
                    if value is Constants.non_constant:
                        ev[dest_block] = True
                        modified = True
                    elif value is Constants.unused:
                        break  # Stop further updates to this block
                    else: # Definite jump found
                        modified = True
                        if check_jmp_condition(jmp_type, value):
                            ev[dest_block] = True
                            definite_jmp = True
                        else:
                            ev[dest_block] = False
                            break
    return modified

def update_dest(instr: Instr, dest: str, val: dict):
    if instr.arg2:
        val[dest] = eval(str(instr.ag1) + instr.opcode + str(instr.arg2))
    else:
        val[dest] = eval(instr.opcode + str(instr.arg1))


def update_val(cfg: CFG, ev: dict, val: dict) -> bool:
    '''Update the map val and return true if any modifications
    are made'''
    modified = False
    for block, executed in ev.items():
        if executed:
            for instr in cfg._blockmap[block].instrs():
                dest = instr.dest
                opcode = instr.opcode
                if opcode == 'phi':
                    pass
                    # FIXME
                else:
                    if all(val[arg] not in {Constants.non_constant, Constants.unused} for arg in instr.uses()):
                        val[dest] = update_dest(instr, val)
                    elif any(val[arg] is Constants.non_constant for arg in instr.uses()):
                        val[dest] = Constants.non_constant
                    

                




    #                 else:
    #                 # FIXME:
    #                 # Replace with set of tuples
    #                 values = {ev[label_block]: val[temp]
    #                           for label_block, temp in instruction.uses}
    #                 if (True, Constants.non_constant) in values.items():
    #                     val[dest] = Constants.non_constant
    #                 else:
    #                     change_phi = False
    #                     for (label_block, temp) in values:
    #                         if not change_phi:
    #                             if val[temp] not in no_value:

    #                                 for (label_block2, temp2) in values:
    #                                     if val[temp2] not in no_value and val[temp2] != val[temp]:
    #                                         val[dest] = Constants.non_constant
    #                                         change_phi = True

    #                                 if False not in [(temp2 == temp or val[temp2] == val[temp] or not ev[label_block2]) for label_block2, temp2 in instruction.uses]:
    #                                     val[dest] = val[temp]
    #                                     change_phi = True

    # return change


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
    modified = True
    while modified:
        modified = False
        modified |= update_ev(cfg, ev, val)
        modified |= update_val(cfg, ev, val)
    remove_blocks(cfg, ev, val)
    remove_instrs(cfg, ev, val)


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
