import argparse
import json
import sys
from enum import Enum, auto
from typing import List, Union

from cfg import CFG, Block, infer, linearize
from ssagen import crude_ssagen
from tac import Instr, Proc, load_tac, Gvar, execute


class Constants(Enum):
    unused = auto()
    non_constant = auto()


def fetch_temporaries(cfg: CFG):
    '''Fetch all the temporaries in the ssa'''
    temps = set()
    for label, block in cfg._blockmap.items():
        for instruction in block.instrs():
            if instruction.opcode != "phi":
                for temp in instruction.uses():
                    temps.add(temp)
            else:
                for temp in instruction.uses():
                    temps.add(temp[1])

            temps.add(instruction.dest)

    return list(temps)


def initialize_conditions(cfg: CFG):
    '''Initialise the maps Val and Ev'''
    val = dict()
    for v in fetch_temporaries(cfg):
        if v and v[1].isalpha():
            val[v] = Constants.non_constant
        else:
            val[v] = Constants.unused

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
            # print("entry",block)
            for jmp in cfg._blockmap[block].reversed_jumps():

                jmp_type = jmp.opcode

                if jmp_type == "jmp" and not definite_jmp:
                    dest_block = jmp.arg1

                    modified |= update_dict(ev, dest_block, True)
                elif jmp_type != "ret":

                    value = val[jmp.arg1]
                    dest_block = jmp.arg2

                    if value is Constants.non_constant:
                        # print("yo",ev)
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


binops = {
    'add': (lambda u, v: u + v),
    'sub': (lambda u, v: u - v),
    'mul': (lambda u, v: u * v),
    'div': (lambda u, v: int(u / v)),
    'mod': (lambda u, v: u - v * int(u / v)),
    'and': (lambda u, v: u & v),
    'or': (lambda u, v: u | v),
    'xor': (lambda u, v: u ^ v),
    'shl': (lambda u, v: u << v),
    'shr': (lambda u, v: u >> v),
}
unops = {
    'neg': (lambda u: -u),
    'not': (lambda u: ~u),
}


def update_dest(instr: Instr, dest: str, val: dict):
    '''Make an update to the dictionary val based on the instruction
    and return true if the dictionary was modified'''
    # FIXME : when the instruction is param, the first the function triggers an error
    # FIXME : need a dictionnary to map optcode to symbol for the eval function : example : "add" --> "+"
    old_value = val[dest]
    if instr.opcode in binops:
        val[dest] = binops[instr.opcode](instr.arg1, instr.arg2)
    elif instr.opcode == 'const':
        val[dest] = instr.arg1
    elif instr.opcode in unops:
        val[dest] = unops[instr.opcode](instr.arg1)
    return old_value != val[dest]


def update_val(cfg: CFG, ev: dict, val: dict) -> bool:
    '''Update the map val and return true if any modifications
    are made'''
    consts = {Constants.unused, Constants.non_constant}
    modified = False
    for block, executed in ev.items():
        if executed:
            for instr in cfg._blockmap[block].body:
                dest = instr.dest
                opcode = instr.opcode
                if opcode == 'phi':
                    for i, (label_i, temporary_i) in enumerate(instr.uses()):

                        if val[temporary_i] not in ({val[dest]} | consts) and val[dest] not in consts:
                            modified |= update_dict(
                                val, dest, Constants.non_constant)

                        elif val[temporary_i] is Constants.non_constant and temporary_i[1].isdigit() and ev[label_i]:
                            modified |= update_dict(
                                val, dest, Constants.non_constant)

                        elif val[temporary_i] not in consts:
                            condition = True
                            for j, (label_j, temporary_j) in enumerate(instr.uses()):
                                if i != j:
                                    if not (val[temporary_j] is Constants.unused or not ev[label_j] or val[temporary_j] == val[temporary_i]):
                                        condition = False
                            if condition:
                                modified |= update_dict(
                                    val, dest, val[temporary_i])
                else:
                    if opcode == "call":
                        modified |= update_dict(
                            val, dest, Constants.non_constant)

                    elif all(val[arg] not in {Constants.non_constant, Constants.unused} for arg in instr.uses()):
                        modified |= update_dest(instr, dest, val)
                    elif any(val[arg] is Constants.non_constant for arg in instr.uses()):
                        modified |= update_dict(
                            val, dest, Constants.non_constant)
    # print(val)
    return modified


def remove_instrs(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    instructions.
    '''
    new_blocks = []

    for label, block in cfg.items():
        new_body = []
        for instr in block.body:
            # print("--")
            # print()
            #print([use[1] if isinstance(use,tuple) else use for use in instr.uses()])
            # print(val)
            try:
                if not any([val[use[1]] == Constants.unused if isinstance(use, tuple) else val[use] == Constants.unused for use in instr.uses()]):
                    new_body.append(instr)
                # print("ok")
            except:
                print('bug', instr)

        # Adding block.jumps in the new block is a potential bug
        new_blocks.append(Block(label, new_body, block.jumps))

    return CFG(cfg.proc_name, cfg.lab_entry, new_blocks)


def remove_blocks(cfg: CFG, ev: dict, val: dict):
    '''When ev and val are fully updated, removed redundant
    blocks. Modifies the cfg inplace.
    '''
    for label_block in ev:

        if not ev[label_block]:
            #dest = cfg._blockmap[label_block].jumps[-1].arg1

            for block in cfg._blockmap:
                new_jump_list = []
                for jump in cfg._blockmap[block].jumps:
                    if not (jump.arg1 == label_block or jump.arg2 == label_block):
                        new_jump_list.append(jump)
                cfg._blockmap[block].jumps = new_jump_list
            cfg.remove_node(cfg._blockmap[label_block])

            # if jump.arg1 == label_block :
            #     jump.arg1 = dest
            # if jump.arg2 == label_block :
            #     jump.arg2 = dest

            # for instr in cfg._blockmap[block].body :
            #     if instr.opcode == "phi" :
            #         print("phi",instr.arg1)
            #         for label, temp in instr.arg1.items() :
            #             if label == label_block :
            #                 for label_pred in list(cfg._fwd[label_block]) :
            #                 instr.arg1[]
            #                 print("forc",cfg._fwd[label_block])


def replace_temporary(cfg: CFG, ev: dict, val: dict):
    '''Whenever we have Val(u) = c ∈ {T,⊥}, we replace u 
    with c and delete the instruction that sets u 
    '''

    # Replace i with c :

    not_consts = {Constants.unused, Constants.non_constant}

    for block in cfg._blockmap:
        for instr in block.body:
            if val[instr.dest] not in not_consts:
                instr.dest = val[instr.dest]
            if instr.opcode != "phi":
                if val[instr.arg1] not in not_consts:
                    instr.arg1 = val[instr.arg1]
                if val[instr.arg2] not in not_consts:
                    instr.arg2 = val[instr.arg2]
            else:
                pass

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
    linearize(decl, cfg)
    remove_blocks(cfg, ev, val)

    cfg = remove_instrs(cfg, ev, val)


def execute(tac_list: List):
    """Execute a TAC program"""
    gvars, procs = dict(), dict()
    for decl in tac_list:
        if isinstance(decl, Gvar):
            gvars[decl.name] = decl
        elif isinstance(decl, Proc):
            procs[decl.name] = decl
    execute(gvars, procs, '@main', [])


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
    for count, decl in enumerate(tac_list):
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
