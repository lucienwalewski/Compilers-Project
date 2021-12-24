#!/usr/bin/env python3

from typing import Union, List
import inspect

"""
A class hierarchy for the AST of the BX language.
"""

####################
# Nodes


from typing import Type

__scopes = []
declarations = []
declarations_line = {}


def reset():
    global declarations, declarations_line
    declarations = []
    declarations_line = {}


class Node:
    """Superclass of all AST nodes"""
    vardecls = {}
    fname = None

    def __init__(self, sloc):
        """
        sloc -- source location linenumber
        """
        self.sloc = sloc


class Ty(Node):
    def __init__(self, sloc, ty: str):
        super().__init__(sloc)
        assert ty in ['int', 'bool', 'void']  # Unnecessary
        self.ty_str = ty

    @ property
    def js_obj(self):
        # FIXME
        pass


class Stmt(Node):
    """Superclass of all statements"""

    def __init__(self, sloc):
        super().__init__(sloc)
        self.ty: Ty

    def type_check(self, scopes, return_type: Ty, context):
        pass

    def find_variable_type(self, var, scopes) -> str:
        for scope in reversed(scopes):
            if var in scope:
                return scope[var]
        raise ValueError(f'Variable {var} not declared at line {self.sloc}')


####################
# Declarations


####################
# Blocks

class Block(Stmt):
    def __init__(self, sloc, stmts: List[Stmt]):

        super().__init__(sloc)
        self.stmts = stmts

    def type_check(self, scopes, return_type: Ty, context):
        '''Type check block by pushing new scope at start
        which is popped at the end'''
        scopes.append(dict())
        return_statement = False

        for stmt in self.stmts:
            if isinstance(stmt, Jump) and "while" not in context:
                raise Exception(f"{stmt.op} outside of loop")

            else:
                return_statement |= stmt.type_check(
                    scopes, return_type, context)
        scopes.pop()
        return return_statement

    @property
    def js_obj(self):
        return {'tag': 'Block',
                'stmts': [stmt.js_obj for stmt in self.stmts]}


####################
# Expressions

class Expr(Node):
    """Superclass of all expressions"""

    def __init__(self, sloc):
        super().__init__(sloc)
        self.ty: Ty


class Variable(Expr):
    """Program variable"""

    def __init__(self, sloc, name: str, type: str = None) -> None:
        """
        name -- string representation of the name of the variable
        """
        super().__init__(sloc)
        self.name = name
        if type:
            self.ty = Ty(self.sloc, type)

    def type_check(self, scopes, return_type: Ty, context) -> None:
        for scope in reversed(scopes):
            if self.name in scope:
                self.ty = Ty(None, scope[self.name])
                return False
        raise ValueError(
            f'{self.name}:line {self.sloc}:Error:Undeclared variable "{self.name}"')

    @property
    def js_obj(self):
        return {'tag': 'Variable',
                'type': self.ty,
                'name': self.name}


class Number(Expr):
    """Number literal"""

    def __init__(self, sloc, value: int) -> None:
        """
        value -- int representing the value of the number
        """
        super().__init__(sloc)
        self.value = value
        self.ty = Ty(self.sloc, 'int')

    def type_check(self, scopes, return_type: Ty, context) -> None:
        if (self.value >> 63) not in [-1, 0]:
            raise ValueError(
                f'line {self.sloc}:Error:Number "{self.value}" out of range [0, 2<<63)')
        return False

    @property
    def js_obj(self):
        return {'tag': 'Number',
                'value': str(self.value)}


class Bool(Expr):
    '''Boolean true or false'''

    def __init__(self, sloc, value: bool):
        super().__init__(sloc)
        '''
        value -- bool representing whether the expression is true or false
        '''
        self.value = value
        self.ty = Ty(self.sloc, 'bool')

    def type_check(self, scopes, return_type: Ty, context):
        return False

    @property
    def js_obj(self):
        return {'tag': 'Bool',
                'value': 1 if self.value else 0}


class OpApp(Expr):
    """Operator application"""

    def __init__(self, sloc, op: str, args):
        """
        op -- string representation of the operator
        args -- operands (all Expr instances)
        """
        super().__init__(sloc)
        assert isinstance(op, str), op
        self.op = op
        self.args = tuple(args)     # make container class explicitly a tuple

    def type_check(self, scopes, return_type: Ty, context=None) -> None:
        '''Recursively type check expression'''
        for arg in self.args:
            arg.type_check(scopes, return_type, context)

        if self.op in {'PLUS', 'MINUS', 'TIMES', 'DIV',
                       'MODULUS', 'BITAND', 'BITOR', 'BITXOR',
                       'BITSHL', 'BITSHR', 'NEG', 'BITCOMPL'
                       } and all([arg.ty.ty_str == 'int' for arg in self.args]):
            self.ty = Ty(self.sloc, 'int')
            if self.op == 'MINUS' and len(self.args) == 1:
                self.op = 'UMINUS'
        elif self.op in {'EQUALITY', 'DISEQUALITY',
                         'LT', 'LEQ', 'GT', 'GEQ'
                         } and all([arg.ty.ty_str == 'int' for arg in self.args]):
            self.ty = Ty(self.sloc, 'bool')
        elif self.op in {'BOOLAND', 'BOOLOR', 'BOOLNEG'
                         } and all([arg.ty.ty_str == 'bool' for arg in self.args]):
            self.ty = Ty(self.sloc, 'bool')
        else:
            raise TypeError(
                f'Operation {self.op} not defined for arguments {self.args} with types {tuple([arg.ty.ty_str for arg in self.args])} at line {self.sloc}')
        return False

    @property
    def js_obj(self):
        return {'tag': 'OpApp',
                'op': self.op,
                'args': [arg.js_obj for arg in self.args]}

####################
# Statements


class IfElse(Stmt):
    def __init__(self, sloc, condition: Expr, block: Block, ifrest):
        '''
        condition -- condition to enter the block
        block -- list of statements to execute
        ifrest -- else blocks of type Block or IfElse
        '''
        super().__init__(sloc)
        assert isinstance(ifrest, (Block, IfElse))
        self.condition = condition
        self.block = block
        self.ifrest = ifrest

    def type_check(self, scopes, return_type: Ty, context) -> None:
        '''Type check IfElse'''
        return_statement = False
        self.condition.type_check(scopes, return_type, context)
        if self.condition.ty.ty_str != 'bool':
            raise TypeError(
                f'IfElse condition must be of type bool - cannot be of type {self.condition.ty} at line {self.sloc}')
        context.append("if")
        if_return_statement = self.block.type_check(
            scopes, return_type, context)
        return_statement |= (self.ifrest.type_check(
            scopes, return_type, context) and if_return_statement)
        return return_statement

    @property
    def js_obj(self):
        return {'tag': 'IfElse',
                'condition': self.condition.js_obj,
                'block': self.block.js_obj,
                'ifrest': self.ifrest.js_obj}


class While(Stmt):
    def __init__(self, sloc, condition: Expr, block: Block):
        '''
        condition -- condition to enter the block
        block -- list of statements
        '''
        super().__init__(sloc)
        self.condition = condition
        self.block = block

    def type_check(self, scopes, return_type: Ty, context) -> None:
        self.condition.type_check(scopes, return_type, context)
        if self.condition.ty.ty_str != 'bool':
            raise TypeError(
                f'While condition must be of type bool - cannot be of type {self.condition.ty.ty_str} at line {self.sloc}')
        context.append("while")
        self.block.type_check(scopes, return_type, context)
        return False

    @property
    def js_obj(self):
        return {'tag': 'While',
                'condition': self.condition.js_obj,
                'stmts': self.block.js_obj}


class Jump(Stmt):
    def __init__(self, sloc, op: str):
        super().__init__(sloc)
        self.op = op

    def type_check(self, var_tys, return_type: Ty, context):
        return False

    @property
    def js_obj(self):
        return {'tag': self.op.capitalize()}


class Assign(Stmt):
    """Assignments"""

    def __init__(self, sloc, var: Variable, expr: Expr):
        """
        var -- a Variable instance
        expr -- an Expr instance
        """
        super().__init__(sloc)
        self.var = var
        self.expr = expr

    def type_check(self, scopes, return_type: Ty, context) -> None:
        '''Type check an assignment. Check that variable was previously
        declared and that types of expr and var match'''
        self.var.type_check(scopes, return_type, context)
        var_type = self.find_variable_type(self.var.name, scopes)
        self.expr.type_check(scopes, return_type, context)
        if var_type != self.expr.ty.ty_str:
            raise TypeError(
                f"Assignment of variable '{self.var.name}' of type '{var_type}' to expr of type '{self.expr.ty.ty_str}' at line {self.sloc}")

        return False

    @property
    def js_obj(self):
        return {'tag': 'Assign',
                'lhs': self.lhs.js_obj,
                'rhs': self.rhs.js_obj}


class Eval(Stmt):
    '''Evaluations'''

    def __init__(self, sloc, expr: Expr):
        super().__init__(sloc)
        self.expr = expr

    def type_check(self, scopes, return_type: Ty, context):
        '''Type check the expression of an e,valuation'''

        self.expr.type_check(scopes, return_type, context)
        return False

    @property
    def js_obj(self):
        # FIXME
        pass


class Call(Expr):
    """Procedure call"""

    def __init__(self, sloc, func: str, exprs: List[Expr]):
        super().__init__(sloc)
        self.func = func
        self.exprs = exprs

    def type_check(self, scopes, return_type: Ty, context) -> None:
        if self.func == 'print':
            assert len(self.exprs) == 1
            expr = self.exprs[0]
            expr.type_check(scopes, return_type, context)
            if expr.ty.ty_str == 'int':
                self.func = '__bx_print_int'
            elif expr.ty.ty_str == 'bool':
                self.func = '__bx_print_bool'
            else:
                raise TypeError(
                    f'Cannot print expressions of type: {expr.ty}')
            self.ty = Ty(self.sloc, "void")
        else:
            func_type = self.find_function_type(self.func, scopes) 
            ret_ty = func_type[1]
            if len(func_type[0]) != len(self.exprs):
                raise ValueError(f'Incorrect number of expressions given for function {self.func}')
            for i, arg in enumerate(self.exprs):
                arg.type_check(scopes, return_type, context)
                if arg.ty.ty_str != func_type[0][i][1]:
                    raise ValueError(f'Incorrect type for argument {func_type[0][i][0]}')
            self.ty = Ty(self.sloc, ret_ty)

        return False

    def find_function_type(self, func, scopes) -> str:
        for scope in reversed(scopes):
            if func in scope:
                return scope[func]
        raise ValueError(f'Procedure {func} not declared at line {self.sloc}')


class Return(Stmt):
    def __init__(self, sloc, expr: Expr):
        super().__init__(sloc)
        self.expr = expr
        if expr is None:
            self.ty = Ty(self.sloc, 'void')

    def type_check(self, scopes, return_type: Ty, context) -> None:
        if self.expr is not None:
            self.expr.type_check(scopes, return_type, context)
            self.ty = self.expr.ty
        if self.ty.ty_str != return_type.ty_str:
            raise ValueError(
                f'"return value type {self.ty.ty_str} does not match the function type {return_type.ty_str}" ')

        return True

    @ property
    def js_obj(self):
        # FIXME
        pass


class Decl(Node):
    '''Superclass of declarations'''

    def __init__(self, sloc):
        super().__init__(sloc)


class Varinit(Decl):
    '''Variable init'''

    def __init__(self, sloc, var: Variable, expr: Expr):
        '''
        var -- a Variable instance
        expr -- an Expr instance
        '''
        super().__init__(sloc)
        self.var = var
        self.expr = expr

    def type_check_global(self, global_scope: dict, var_type: Ty) -> None:
        '''Type check global variables and add type to global scope'''
        if self.var.name in global_scope:
            raise ValueError(f'Duplicate declaration of {self.var.name}')
        if not isinstance(self.expr, (Number, Bool)):
            raise ValueError(f'Global variables must be declared as constants')
        if self.expr.ty.ty_str != var_type.ty_str:
            raise ValueError(
                f'{self.var.name} of incorrect type. Expected {var_type.ty_str}. Obtained {self.expr.ty.ty_str}')
        global_scope[self.var.name] = self.expr.ty.ty_str
        self.var.ty = self.expr.ty

    def type_check(self, scopes, var_type: Ty, context) -> None:
        '''Type check a single variable initialisation. Add variable
        to current scope if no errors raised'''
        if self.var.name in scopes[-1]:
            raise ValueError(
                f'Duplicate variable declaration:{self.var.name} at line {self.sloc}')
        self.expr.type_check(scopes, None, context)
        if self.expr.ty.ty_str != var_type.ty_str:
            raise ValueError(
                f'Declaration of variable {self.var.name} of incorrect type')
        self.var.ty = Ty(None, self.expr.ty.ty_str)
        scopes[-1][self.var.name] = self.var.ty.ty_str
        return False

    @ property
    def js_obj(self):
        return {'tag': 'Varinit',
                'lhs': self.var.js_obj,
                'rhs': self.expr.js_obj}


class Vardecl(Decl):
    '''Variable decarations'''

    def __init__(self, sloc, varinits: List[Varinit], ty: Ty) -> None:
        super().__init__(sloc)
        assert len(varinits) > 0
        self.varinits = varinits
        self.ty = ty

    def type_check_global(self, global_scope: dict):
        '''Type check global variables'''
        for varinit in self.varinits:
            varinit.type_check_global(global_scope, self.ty)

    def type_check(self, scopes, return_type: Ty, context) -> None:
        for varinit in self.varinits:
            varinit.type_check(scopes, self.ty, None)
        return False


class Param(Node):
    def __init__(self, sloc, names: List[str], ty: Ty):
        super().__init__(sloc)
        assert len(names) > 0
        self.names = names
        self.ty = ty


class Procdecl(Decl):
    def __init__(self, sloc, name: str, params, return_type: Ty, block: Block) -> None:
        super().__init__(sloc)
        self.name = name
        self.params = params
        self.return_type = return_type
        self.block = block

    def type_check_global(self, global_scope: dict) -> None:
        '''Type check a procedure and add the types to
        the global scope. Scope format for procdels:

        proc_name: ({arg_name1 : arg_type1,...}, return_type)
        '''
        args_type = []
        if self.params is not None:
            for param in self.params:
                for arg_name in param.names:
                    args_type.append((arg_name, param.ty.ty_str))
        if self.name in global_scope:
            raise ValueError(f'Declaration {self.name} already declared')
        global_scope[self.name] = (args_type, self.return_type.ty_str)

    def body_type_check(self, global_scope) -> None:
        '''Type check the body of a procedure'''
        context = ["proc"]
        body_scope = dict(global_scope[0][self.name][0])
        global_scope.append(body_scope)
        return_statement = self.block.type_check(
            global_scope, self.return_type, context)
        if not return_statement and self.return_type.ty_str != "void":
            raise Exception
        if not self.block.stmts or not isinstance(self.block.stmts[-1], Return):
            self.block.stmts.append(Return(0, None))
        global_scope.pop()


####################
# Programs

class Program(Node):
    def __init__(self, sloc, decls: List[Decl]):
        super().__init__(sloc)
        self.decls = decls
        self.type_check_global()
        self.type_check_bodies()

    def type_check_global(self) -> None:
        '''Type check the declarations and add the types
        to the global scope in the first phase of type-checking'''
        global_scope = {}
        main_declared = False
        for decl in self.decls:
            decl.type_check_global(global_scope)
            if isinstance(decl, Procdecl):
                if decl.name == 'main':
                    main_declared = True
        if not main_declared:
            raise ValueError(f'No declaration of main')
        if global_scope['main'][0] or global_scope['main'][1] != 'void':
            raise ValueError(
                f'Incorrect arguments or return type for main declaration')
        self.global_scope = [global_scope]

    def type_check_bodies(self) -> None:
        '''Type check the bodies of the procdecls in the
        second phase of type-checking'''
        for decl in self.decls:
            if isinstance(decl, Procdecl):
                decl.body_type_check(self.global_scope)

    @ property
    def js_obj(self):
        # FIXME
        return {'tag': 'Program',
                'vars': self.lvars,
                'decls': self.decls.js_obj}
