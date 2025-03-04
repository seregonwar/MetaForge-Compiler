from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

@dataclass
class IRInstruction:
    op: str
    args: List[str]
    result: Optional[str] = None

class IRGenerator:
    def __init__(self):
        self.instructions = []
        self.temp_counter = 0
        self.label_counter = 0
        self.current_function = None
        self.current_class = None
        self.string_literals = {}
        self.vtables = {}
        
    def generate(self, ast: Dict) -> List[IRInstruction]:
        """Generate IR from AST"""
        try:
            # First pass: collect class information for vtables
            self._collect_class_info(ast)
            
            # Second pass: generate IR for declarations
            for decl in ast['declarations']:
                self._generate_declaration(decl)
                
            return self.instructions
            
        except Exception as e:
            logging.error(f"IR generation failed: {str(e)}")
            return []
            
    def _collect_class_info(self, ast: Dict):
        """Collect class information for vtables"""
        for decl in ast['declarations']:
            if decl['type'] == 'ClassDeclaration':
                class_name = decl['name']
                vtable = []
                
                # Add parent methods first if exists
                if 'extends' in decl:
                    parent_vtable = self.vtables.get(decl['extends'], [])
                    vtable.extend(parent_vtable)
                    
                # Add/override methods
                for member in decl['body']:
                    if member['type'] == 'MethodDeclaration':
                        method_name = member['name']
                        # Find method slot or append
                        found = False
                        for i, (name, _) in enumerate(vtable):
                            if name == method_name:
                                vtable[i] = (method_name, f"{class_name}_{method_name}")
                                found = True
                                break
                        if not found:
                            vtable.append((method_name, f"{class_name}_{method_name}"))
                            
                self.vtables[class_name] = vtable
                
    def _generate_declaration(self, decl: Dict):
        """Generate IR for a declaration"""
        if decl['type'] == 'ClassDeclaration':
            self.current_class = decl['name']
            
            # Generate vtable
            vtable = self.vtables[decl['name']]
            vtable_label = f"vtable_{decl['name']}"
            self.instructions.append(IRInstruction('vtable', [decl['name']], vtable_label))
            for method_name, impl_name in vtable:
                self.instructions.append(IRInstruction('vtable_entry', [vtable_label, method_name, impl_name]))
                
            # Generate methods
            for member in decl['body']:
                if member['type'] == 'MethodDeclaration':
                    self._generate_method(member)
                    
            self.current_class = None
            
        elif decl['type'] == 'FunctionDeclaration':
            self._generate_function(decl)
            
    def _generate_method(self, method: Dict):
        """Generate IR for a method"""
        self.current_function = f"{self.current_class}_{method['name']}"
        
        # Function prologue
        self.instructions.append(IRInstruction('label', [self.current_function]))
        self.instructions.append(IRInstruction('enter', [str(len(method['parameters']) + 1)]))  # +1 for this
        
        # Store parameters
        self.instructions.append(IRInstruction('store_param', ['0'], 'this'))
        for i, param in enumerate(method['parameters'], 1):
            self.instructions.append(IRInstruction('store_param', [str(i)], param['name']))
            
        # Generate body
        if method['body']:
            for stmt in method['body']:
                self._generate_statement(stmt)
                
        # Function epilogue
        if not method['returnType'] or method['returnType'] == 'void':
            self.instructions.append(IRInstruction('return_void', []))
        self.instructions.append(IRInstruction('leave', []))
        
        self.current_function = None
        
    def _generate_function(self, func: Dict):
        """Generate IR for a function"""
        self.current_function = func['name']
        
        # Function prologue
        self.instructions.append(IRInstruction('label', [func['name']]))
        self.instructions.append(IRInstruction('enter', [str(len(func['parameters']))]))
        
        # Store parameters
        for i, param in enumerate(func['parameters']):
            self.instructions.append(IRInstruction('store_param', [str(i)], param['name']))
            
        # Generate body
        if func['body']:
            for stmt in func['body']:
                self._generate_statement(stmt)
                
        # Function epilogue
        if not func['returnType'] or func['returnType'] == 'void':
            self.instructions.append(IRInstruction('return_void', []))
        self.instructions.append(IRInstruction('leave', []))
        
        self.current_function = None
        
    def _generate_statement(self, stmt: Dict):
        """Generate IR for a statement"""
        if stmt['type'] == 'VariableDeclaration':
            value = self._generate_expression(stmt['initializer'])
            self.instructions.append(IRInstruction('store', [value], stmt['name']))
            
        elif stmt['type'] == 'ExpressionStatement':
            self._generate_expression(stmt['expression'])
            
        elif stmt['type'] == 'ReturnStatement':
            if stmt['value']:
                value = self._generate_expression(stmt['value'])
                self.instructions.append(IRInstruction('return', [value]))
            else:
                self.instructions.append(IRInstruction('return_void', []))
                
        elif stmt['type'] == 'IfStatement':
            cond = self._generate_expression(stmt['condition'])
            else_label = self._new_label()
            end_label = self._new_label()
            
            self.instructions.append(IRInstruction('branch_false', [cond, else_label]))
            
            for s in stmt['thenBranch']:
                self._generate_statement(s)
            self.instructions.append(IRInstruction('jump', [end_label]))
            
            self.instructions.append(IRInstruction('label', [else_label]))
            if stmt['elseBranch']:
                for s in stmt['elseBranch']:
                    self._generate_statement(s)
                    
            self.instructions.append(IRInstruction('label', [end_label]))
            
        elif stmt['type'] == 'WhileStatement':
            start_label = self._new_label()
            end_label = self._new_label()
            
            self.instructions.append(IRInstruction('label', [start_label]))
            cond = self._generate_expression(stmt['condition'])
            self.instructions.append(IRInstruction('branch_false', [cond, end_label]))
            
            for s in stmt['body']:
                self._generate_statement(s)
            self.instructions.append(IRInstruction('jump', [start_label]))
            
            self.instructions.append(IRInstruction('label', [end_label]))
            
    def _generate_expression(self, expr: Dict) -> str:
        """Generate IR for an expression and return temp variable name"""
        if expr['type'] == 'NumberLiteral':
            temp = self._new_temp()
            self.instructions.append(IRInstruction('load_const', [str(expr['value'])], temp))
            return temp
            
        elif expr['type'] == 'StringLiteral':
            if expr['value'] not in self.string_literals:
                label = f"str_{len(self.string_literals)}"
                self.string_literals[expr['value']] = label
                self.instructions.append(IRInstruction('string', [expr['value']], label))
            temp = self._new_temp()
            self.instructions.append(IRInstruction('load_string', [self.string_literals[expr['value']]], temp))
            return temp
            
        elif expr['type'] == 'BinaryExpression':
            left = self._generate_expression(expr['left'])
            right = self._generate_expression(expr['right'])
            result = self._new_temp()
            
            op_map = {
                '+': 'add', '-': 'sub', '*': 'mul', '/': 'div',
                '<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge',
                '==': 'eq', '!=': 'ne', '&&': 'and', '||': 'or'
            }
            
            self.instructions.append(IRInstruction(op_map[expr['operator']], [left, right], result))
            return result
            
        elif expr['type'] == 'UnaryExpression':
            operand = self._generate_expression(expr['operand'])
            result = self._new_temp()
            
            op_map = {'-': 'neg', '!': 'not', '~': 'bit_not'}
            self.instructions.append(IRInstruction(op_map[expr['operator']], [operand], result))
            return result
            
        elif expr['type'] == 'CallExpression':
            if isinstance(expr['callee'], dict) and expr['callee']['type'] == 'MemberAccess':
                # Method call
                obj = self._generate_expression(expr['callee']['object'])
                method_name = expr['callee']['member']
                
                # Load vtable
                vtable = self._new_temp()
                self.instructions.append(IRInstruction('load_vtable', [obj], vtable))
                
                # Get method pointer
                method_ptr = self._new_temp()
                self.instructions.append(IRInstruction('vtable_method', [vtable, method_name], method_ptr))
                
                # Generate argument values
                args = [self._generate_expression(arg) for arg in expr['arguments']]
                
                # Call through method pointer
                result = self._new_temp()
                self.instructions.append(IRInstruction('call_method', [method_ptr, obj] + args, result))
                return result
                
            else:
                # Function call
                args = [self._generate_expression(arg) for arg in expr['arguments']]
                result = self._new_temp()
                self.instructions.append(IRInstruction('call', [expr['callee']['name']] + args, result))
                return result
                
        elif expr['type'] == 'MemberAccess':
            obj = self._generate_expression(expr['object'])
            result = self._new_temp()
            self.instructions.append(IRInstruction('get_field', [obj, expr['member']], result))
            return result
            
        elif expr['type'] == 'Identifier':
            temp = self._new_temp()
            self.instructions.append(IRInstruction('load', [expr['name']], temp))
            return temp
            
        elif expr['type'] == 'ThisExpression':
            return 'this'
            
        elif expr['type'] == 'SuperExpression':
            return 'this'  # super uses same object as this
            
        elif expr['type'] == 'NewExpression':
            # Allocate object
            size = self._new_temp()
            self.instructions.append(IRInstruction('sizeof', [expr['className']], size))
            
            obj = self._new_temp()
            self.instructions.append(IRInstruction('alloc', [size], obj))
            
            # Set vtable
            vtable = f"vtable_{expr['className']}"
            self.instructions.append(IRInstruction('set_vtable', [obj, vtable]))
            
            # Call constructor if exists
            ctor_name = f"{expr['className']}_init"
            self.instructions.append(IRInstruction('call', [ctor_name, obj]))
            
            return obj
            
        return self._new_temp()  # Fallback
        
    def _new_temp(self) -> str:
        """Generate new temporary variable name"""
        temp = f"t{self.temp_counter}"
        self.temp_counter += 1
        return temp
        
    def _new_label(self) -> str:
        """Generate new label name"""
        label = f"L{self.label_counter}"
        self.label_counter += 1
        return label