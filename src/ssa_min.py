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
    modif1, modif2 = False, False
    while modif1 or modif2:
        modif1, cfg = rename(cfg)
        modif2, cfg = NCE(cfg)
    return cfg

def NCE(cfg: CFG) -> CFG:
    modif = False
    modified = True
    while modified:
        modified = False
        block_list = []
        for block in cfg._blockmap.values():
            new_block_instrs = []
            for ins in block.body:
                if ins.opcode == 'phi':
                    if is_nce(ins):
                        modif = True
                        modified = True
                        continue
                new_block_instrs.append(ins)
            block_list.append(
                Block(block.label, new_block_instrs, block.jumps))
        cfg = CFG(cfg.proc_name, cfg.lab_entry, block_list)
    return modif, cfg

def rename(cfg:CFG) -> CFG:
    modif = False
    crude_ssagen(tlv, cfg)
    cfg_copy = copy.deepcopy(cfg)

    for index, instr in enumerate(cfg_copy.instrs()):
        if (instr.opcode == "phi") and is_rn(instr):
            modif = True
            to_replace = instr.dest
            to_use = instr.arg1
            new_blocks = []

            for block in cfg._blockmap.values():
                inst_list = []
                for instru in block.body:
                    if to_replace == instru.dest or to_replace in instru.arg1.values() or to_replace in instru.arg2.values():
                        new_args1 = {}
                        for key, value in instru.arg1.items():
                            new_args1[key] = to_use if value == to_replace else value
                        if instru.arg2:
                            new_args2 = {}
                            for key, value in instru.arg2.items():
                                new_args2[key] = to_use if value == to_replace else value
                        inst_list.append(Instr(to_use if to_replace == instru.dest else instru.dest, instru.opcode, [new_args1, new_args2]))
                    
                new_block = Block(block.label, inst_list, block.jumps)
                new_blocks.append(new_block)

            cfg = CFG(cfg.proc_name, cfg.lab_entry, new_blocks)

    return modif, cfg


def is_nce(ins : tac.Instr) -> bool:
    s = set()
    val = False
    for tmp in ins.arg1.values():
        s.add(tmp)
        if ins == tmp:
            val =True
    return len(s)==1 and val


def is_rn(ins : tac.Instr) -> bool:
    s = set()
    val = False
    for tmp in ins.arg1.values():
        s.add(tmp)
        if ins == tmp:
            val =True
    return len(s)==2 and val


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
            minimize(cfg)
            # make_dotfiles(cfg, tlv.name[1:], args.file[0], args.verbosity)
            # if args.verbosity >= 2:
            #     cfglib.linearize(tlv, cfg)
            #     print(tlv)