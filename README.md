# Compilers-Project

## Participants
- Alban Puech
- Lucien Walewski
- Aurele Bohbot

## Project structure

- [README.md](README.md)
- dataflow.pdf : Project description
- src/ : Source code
    - cfg.py : CFG class file
    - cse.py : Common Subexpression Elimination file
    - dom_tree.py : Dominator Tree file
    - optimize_tac.py : Final deliverable
    - sccp.py : SCCP file
    - ssa_min.py : SSA Minimization file
    - ssagen.py : SSA Generator file
    - tac_doft.py : Lab5 file containing GCE
    - tac.py : TAC class file
    - tacrun.py : TAC Runner file
- data/ : Test files

# File descriptions

In order of importance:

### sccp.py

Contains the sccp algorithm. We first initialize the dictionaries `ev` and `val` before updating them until there are no further changes. Having done this, we can remove the redundant blocks given by `ev` and remove the redundant instructions as well as replace constant temporaries with `val`.

### cse.py

We first apply local cse to each block. This first involves creating a mapping between expressions and the instructions associated to the expressions (given in a set) with the function `expr_map_block`. For expressions seen more than once, we construct a list of all the instructions which modify the temporaries used in the expression. Based on this we can replace expressions with `copy` where possible (i.e. the temporaries were not modified before the copy).

Having performed local cse we can apply global cse to the entire cfg. This involves first computing the dominator tree, the mappings between expressions and instructions for each block as well as the available expressions at the end of each block (i.e. their temporaries have not been modified before the end of the block). Then, iterating over the blocks and their respective strict dominators, we see if we can replace the first expression of the block with a copy. 

> Remark: We only have to consider the first expression of the block as we have already applied local cse to the block. This implies that any subsequent expressions in the block that can be optimised are already in the form of a copy.

### tac_doft.py

GCP was already seen in lab5

### ssa_min.py