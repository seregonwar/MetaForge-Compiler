from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import logging

class IROpCode(Enum):
    # Memory operations
    LOAD = "load"      # Load value into register
    STORE = "store"    # Store value to memory
    LEA = "lea"        # Load Effective Address
    MOV = "mov"        # Move data between registers
    
    # Arithmetic operations
    ADD = "add"
    SUB = "sub" 
    MUL = "mul"
    DIV = "div"
    
    # Flow control
    JMP = "jmp"        # Unconditional jump
    JZ = "jz"         # Jump if zero
    JNZ = "jnz"       # Jump if not zero
    CALL = "call"     # Function call
    RET = "ret"       # Return
    
    # Stack management
    PUSH = "push"
    POP = "pop"
    
    # Comparisons
    CMP = "cmp"
    TEST = "test"

@dataclass
class IRInstruction:
    opcode: IROpCode
    dest: Optional[str] = None
    src1: Optional[str] = None
    src2: Optional[str] = None
    immediate: Optional[int] = None
    label: Optional[str] = None

class IRGenerator:
    def __init__(self):
        self.temp_counter = 0
        self.label_counter = 0
        self.string_literals: Dict[str, str] = {}
        self.current_function: Optional[str] = None
        
    def generate(self, ast: Dict) -> Dict:
        """Generate IR from AST"""
        logging.info("Generating IR from AST...")
        
        try:
            ir = {
                'functions': {},
                'globals': {},
                'strings': self.string_literals,
                'entry_point': '_start'
            }
            
            # Generate initialization code
            ir['init'] = self._generate_init()
            
            # Process global declarations
            for decl in ast['declarations']:
                if decl['type'] == 'Function':
                    logging.debug(f"Processing function: {decl['name']}")
                    ir['functions'][decl['name']] = self._generate_function(decl)
                elif decl['type'] == 'Import':
                    logging.debug(f"Processing import: {decl['path']}")
                    self._process_import(decl, ir)
                    
            logging.info(f"Generated IR with {len(ir['functions'])} functions")
            return ir
            
        except Exception as e:
            logging.error(f"Failed to generate IR: {str(e)}", exc_info=True)
            raise
            
    def _generate_init(self) -> List[Dict]:
        """Generate initialization code"""
        return [
            {'type': 'label', 'name': '_start'},
            # Setup stack frame
            {'type': 'instruction', 'opcode': IROpCode.PUSH, 'operands': ['rbp']},
            {'type': 'instruction', 'opcode': IROpCode.MOV, 'operands': ['rbp', 'rsp']},
            # Reserve stack space
            {'type': 'instruction', 'opcode': IROpCode.SUB, 'operands': ['rsp', 32]},
            # Call main
            {'type': 'instruction', 'opcode': IROpCode.CALL, 'target': 'main'},
            # Cleanup and exit
            {'type': 'instruction', 'opcode': IROpCode.MOV, 'operands': ['rsp', 'rbp']},
            {'type': 'instruction', 'opcode': IROpCode.POP, 'operands': ['rbp']},
            {'type': 'instruction', 'opcode': IROpCode.RET}
        ]
            
    def _generate_function(self, node: Dict) -> Dict:
        """Generate IR for a function"""
        self.current_function = node['name']
        
        function = {
            'name': node['name'],
            'params': node.get('params', []),
            'return_type': node.get('return_type', 'void'),
            'stack_size': 0,
            'instructions': []
        }
        
        # Function prologue
        function['instructions'].extend([
            {'type': 'label', 'name': node['name']},
            {'type': 'instruction', 'opcode': IROpCode.PUSH, 'operands': ['rbp']},
            {'type': 'instruction', 'opcode': IROpCode.MOV, 'operands': ['rbp', 'rsp']},
            {'type': 'instruction', 'opcode': IROpCode.SUB, 'operands': ['rsp', 32]}  # Shadow space
        ])
        
        # Generate IR for function body
        if 'body' in node:
            for stmt in node['body']['statements']:
                ir_stmt = self._generate_statement(stmt)
                function['instructions'].extend(ir_stmt)
                
        # Function epilogue if no return present
        if not function['instructions'] or function['instructions'][-1]['opcode'] != IROpCode.RET:
            function['instructions'].extend([
                {'type': 'instruction', 'opcode': IROpCode.MOV, 'operands': ['rsp', 'rbp']},
                {'type': 'instruction', 'opcode': IROpCode.POP, 'operands': ['rbp']},
                {'type': 'instruction', 'opcode': IROpCode.RET}
            ])
            
        return function
        
    def _generate_statement(self, node: Dict) -> List[Dict]:
        """Generate IR for a statement"""
        if node['type'] == 'FunctionCall':
            return self._generate_call(node)
        elif node['type'] == 'Return':
            return self._generate_return(node)
        else:
            logging.warning(f"Unsupported statement type: {node['type']}")
            return []
            
    def _generate_call(self, node: Dict) -> List[Dict]:
        """Generate IR for a function call"""
        instructions = []
        
        # Load arguments into registers
        arg_regs = ['rcx', 'rdx', 'r8', 'r9']  # Windows x64 calling convention
        for i, arg in enumerate(node['arguments']):
            if i < len(arg_regs):
                if arg['type'] == 'StringLiteral':
                    # Add string to data section
                    str_label = f'str_{len(self.string_literals)}'
                    self.string_literals[str_label] = arg['value']
                    
                    instructions.append({
                        'type': 'instruction',
                        'opcode': IROpCode.LEA,
                        'operands': [arg_regs[i], str_label]
                    })
                elif arg['type'] == 'NumberLiteral':
                    instructions.append({
                        'type': 'instruction',
                        'opcode': IROpCode.MOV,
                        'operands': [arg_regs[i], arg['value']]
                    })
                    
        # Function call
        instructions.append({
            'type': 'instruction',
            'opcode': IROpCode.CALL,
            'target': node['name']
        })
        
        return instructions
        
    def _generate_return(self, node: Dict) -> List[Dict]:
        """Generate IR for a return statement"""
        instructions = []
        
        if 'value' in node:
            if node['value']['type'] == 'NumberLiteral':
                instructions.append({
                    'type': 'instruction',
                    'opcode': IROpCode.MOV,
                    'operands': ['rax', node['value']['value']]
                })
                
        # Function epilogue
        instructions.extend([
            {'type': 'instruction', 'opcode': IROpCode.MOV, 'operands': ['rsp', 'rbp']},
            {'type': 'instruction', 'opcode': IROpCode.POP, 'operands': ['rbp']},
            {'type': 'instruction', 'opcode': IROpCode.RET}
        ])
        
        return instructions
        
    def _new_temp(self) -> str:
        """Generate a new temporary name"""
        self.temp_counter += 1
        return f't{self.temp_counter}'
        
    def _new_label(self) -> str:
        """Generate a new label"""
        self.label_counter += 1
        return f'L{self.label_counter}'
        
    def _add_string(self, value: str) -> int:
        """Add a string to the data section"""
        str_label = f'str_{len(self.string_literals)}'
        self.string_literals[str_label] = value
        return len(self.string_literals) - 1
        
    def _process_import(self, node: Dict, ir: Dict):
        """Process an import declaration"""
        # Add imported functions to IR
        if 'functions' in node:
            for func in node['functions']:
                ir['functions'][func['name']] = {
                    'name': func['name'],
                    'params': func.get('params', []),
                    'return_type': func.get('return_type', 'void'),
                    'external': True
                }