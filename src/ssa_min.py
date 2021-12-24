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

def minimize(cfg : CFG) -> CFG:
    """Performs minimization"""
    modif1, modif2 = True, True
    while modif1 or modif2: 
        # We run the minimization until there are no more modification
        modif1, cfg = NCE(cfg)
        modif2, cfg = rename(cfg)  
    return cfg

def show_cfg(cfg : CFG):
    """Displays a cfg"""
    for instr in cfg.instrs():
        print(instr)

def NCE(cfg: CFG) -> CFG:
    """Performs null choice elimination"""
    modif = False
    modified = True
    while modified: 
        # We continue to run NCE utnil there are no more modification
        modified = False
        block_list = []
        for block in cfg._blockmap.values():
            new_block_instrs = []
            for ins in block.body:
                if ins.opcode == 'phi' and is_nce(ins):
                    # Instruction has to be eliminated
                    # We have modified the cfg
                    modif = True
                    modified = True
                else:
                    # Otherwise we keep the instruction in cfg
                    new_block_instrs.append(ins)
            block_list.append(
                Block(block.label, new_block_instrs, block.jumps))
        cfg = CFG(cfg.proc_name, cfg.lab_entry, block_list)
    return modif, cfg

def rename(cfg:CFG) -> CFG:
    """Performs renaming"""
    modif = False
    cfg_copy = copy.deepcopy(cfg)
    for index, instr in enumerate(cfg_copy.instrs()):
        if (instr.opcode == "phi") and is_rn(instr):
            # We found an instruction that has to be renamed
            modif = True
            to_replace = instr.dest # Temp that we should replace
            to_use = set(list(instr.arg1.values())) 
            if to_replace in to_use: to_use.remove(to_replace)
            try:
                to_use = to_use.pop() # Temp we should use instead
            except:
                print(to_replace , to_use)
                raise KeyError
            
            new_blocks = []
            for block in cfg._blockmap.values():
                # We iterate over the cfg to edit the instruction that have to be
                inst_list = []
                for instru in block.body:
                    if (instru.opcode == "phi" and (to_replace == instru.dest or to_replace in instru.arg1.values())):
                        new_args1 = {}
                        for key, value in instru.arg1.items():
                            new_args1[key] = to_use if value == to_replace else value
                        new_args2 = {}
                        if instru.arg2:
                            for key, value in instru.arg2.items():
                                new_args2[key] = to_use if value == to_replace else value
                        inst_list.append(Instr(to_use if to_replace == instru.dest else instru.dest, instru.opcode,
                                        [new_args1, new_args2] if new_args2 else [new_args1]))
                    elif (instru.opcode != "phi" and (to_replace == instru.dest or to_replace in {instru.arg1, instru.arg2})):
                        new_args1 = to_use if instru.arg1 == to_replace else instru.arg1
                        if instru.arg2:
                            new_args2 = to_use if instru.arg2 == to_replace else instru.arg2
                        else:
                            new_args2 = False
                        inst_list.append(Instr(to_use if to_replace == instru.dest else instru.dest, instru.opcode,
                                        [new_args1, new_args2] if new_args2 else [new_args1]))
                    else:
                        inst_list.append(instru)
                new_block = Block(block.label, inst_list, block.jumps)
                new_blocks.append(new_block)

            cfg = CFG(cfg.proc_name, cfg.lab_entry, new_blocks)
    return modif, cfg


def is_nce(ins : tac.Instr) -> bool:
    """Check if an instruction has to be null choice eliminated"""
    s = set()
    val = False
    for tmp in ins.arg1.values():
        s.add(tmp)
        if ins.dest == tmp:
            val =True
    return len(s)==1 and ins.dest in s


def is_rn(ins : tac.Instr) -> bool:
    """Check if an instruction has to be renamed"""
    s = set()
    val = False
    for tmp in ins.arg1.values():
        s.add(tmp)
        if ins.dest == tmp:
            val =True
    return (len(s)==2 and val) or len(s)==1


if __name__=='__main__':
    import os
    from argparse import ArgumentParser
    ap = ArgumentParser(description='TAC library, parser, and interpreter')
    ap.add_argument('file', metavar='FILE', type=str, nargs=1, help='A TAC file')
    ap.add_argument('-v', dest='verbosity', default=0, action='count',
                    help='increase verbosity')
    args = ap.parse_args()
    gvars, procs = dict(), dict()
    for tlv in tac.load_tac(args.file[0]):
        if isinstance(tlv, tac.Proc):
            cfg = cfglib.infer(tlv)
            crude_ssagen(tlv, cfg)
            for ins in cfg.instrs():
                print(ins)
            print('\n\n')
            cfg = minimize(cfg)
            # print(tlv)
            for ins in cfg.instrs():
                print(ins)
            print('\n\n')
            # make_dotfiles(cfg, tlv.name[1:], args.file[0], args.verbosity)
            # if args.verbosity >= 2: