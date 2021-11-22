import sys
import argparse
from typing import List, Union

from cfg import *
from ssagen import *
from tac import *
import copy


def DSE(cfg: CFG) -> CFG:
    """
    Global Dead Store Elimination
    """
    modified = True
    while modified:
        modified = False
        livein, liveout = dict(), dict()
        recompute_liveness(cfg, livein, liveout)

        block_list = []
        for block_label, block in cfg._blockmap.items():
            new_block_instrs = []
            for ins in block.body:
                if ins.opcode not in ('div', 'mod', 'call'):
                    # Check if dead store
                    if ins.dest and ins.dest not in liveout[ins] and ins.dest.startswith('%'):
                        modified = True
                        continue
                new_block_instrs.append(ins)
            block_list.append(
                Block(block.label, new_block_instrs, block.jumps))
        cfg = CFG(cfg.proc_name, cfg.lab_entry, block_list)
    return cfg


def GCP(tlv, cfg: CFG) -> CFG:
    """
    Global Copy Propagation. This is a one-shot procedure.
    """
    new_body = []
    crude_ssagen(tlv, cfg)
    cfg_copy = copy.deepcopy(cfg)

    # iterate over all instructions
    for index, instr in enumerate(cfg_copy.instrs()):
        # look for copy instructions
        if instr.opcode == "copy":
            to_replace = instr.dest
            to_use = instr.arg1
            new_blocks = []

            # iterate over all blocks
            for block in cfg._blockmap.values():
                inst_list = []
                for instru in block.body:

                    # change the old temp name by the new one in phi functions
                    if instru.opcode == "phi":
                        new_arg = dict()
                        for label, temp in instru.arg1.items():
                            new_arg[label] = temp if temp != to_replace else to_use
                        inst_list.append(Instr(
                            to_use if instru.dest == to_replace else instru.dest, instru.opcode, [new_arg]))

                    # change the old temp name by the new one in other instructions and discard the original copy instruction
                    elif instru.opcode != "copy" or instru.arg1 != to_use or instru.dest != to_replace:
                        inst_list.append(Instr(to_use if instru.dest == to_replace else instru.dest, instru.opcode, [
                                         (to_use if arg == to_replace else arg) for arg in [instru.arg1, instru.arg2]]))

                # create new block with new instructions
                new_block = Block(block.label, inst_list, block.jumps)
                new_blocks.append(new_block)

            # update cfg
            cfg = CFG(cfg.proc_name, cfg.lab_entry, new_blocks)

    return cfg


def optimize_decl(tac_proc: Union[Gvar, Proc]) -> None:
    """
    Optimize a declaration. First perform DSE as many times as necessary,
    then GCP. 
    """
    cfg = infer(tac_proc)
    cfg = DSE(cfg)
    cfg = GCP(tac_proc, cfg)
    linearize(tac_proc, cfg)


def execute(tac_list: List):
    """Execute a TAC program"""
    gvars, procs = dict(), dict()
    for decl in tac_list:
        if isinstance(decl, Gvar):
            gvars[decl.name] = decl
        elif isinstance(decl, Proc):
            procs[decl.name] = decl
    tac.execute(gvars, procs, '@main', [])


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
            optimize_decl(decl)
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
