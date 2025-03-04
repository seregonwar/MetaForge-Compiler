from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Iterator
from enum import Enum
from pathlib import Path

class SymbolType(Enum):
    FUNCTION = "function"
    VARIABLE = "variable" 
    STRUCT = "struct"
    ENUM = "enum"
    TYPE = "type"

@dataclass
class Symbol:
    name: str
    type: SymbolType
    data_type: str
    scope: str
    location: tuple  # (line, column)
    is_mutable: bool = True
    is_exported: bool = False
    references: List['Symbol'] = None
    documentation: str = ""

class Scope:
    def __init__(self, name: str, parent: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List[Scope] = []
        
    def add_symbol(self, symbol: Symbol) -> bool:
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True
        
    def lookup(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None
        
    def add_child(self, child: 'Scope'):
        """Adds a child scope"""
        child.parent = self
        self.children.append(child)

class TypeInfo:
    def __init__(self, name: str, is_primitive: bool = False):
        self.name = name
        self.is_primitive = is_primitive
        self.fields = {}  # name -> type
        self.methods = {}  # name -> (return_type, param_types)
        self.parent = None
        self.interfaces = []
        
    def add_field(self, name: str, field_type: str):
        self.fields[name] = field_type
        
    def add_method(self, name: str, return_type: str, param_types: List[str]):
        self.methods[name] = (return_type, param_types)
        
    def get_field_type(self, name: str):
        return self.fields.get(name)
        
    def get_method_info(self, name: str):
        return self.methods.get(name)

class SemanticAnalyzer:
    def __init__(self, diagnostics=None):
        self.types = {}  # name -> TypeInfo
        self.current_class = None
        self.errors = []
        self.diagnostics = diagnostics
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.warnings = []
        self.used_symbols = set()
        
        # Add primitive types
        for type_name in ['i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64',
                         'f32', 'f64', 'bool', 'string']:
            self.types[type_name] = TypeInfo(type_name, True)
            
    def analyze(self, ast: Dict) -> bool:
        """Performs complete semantic analysis"""
        try:
            # First pass: collect all types
            self._collect_types(ast)
            
            # Second pass: validate type relationships
            self._validate_types()
            
            # Third pass: analyze declarations
            if 'declarations' in ast:
                for decl in ast['declarations']:
                    self._analyze_declaration(decl)
                    
            # Fourth pass: additional checks
            self._check_unused_symbols()
            
            return len(self.errors) == 0
            
        except Exception as e:
            if self.diagnostics:
                self.diagnostics.error(f"Fatal semantic error: {str(e)}")
            self.errors.append(f"Fatal semantic error: {str(e)}")
            return False
            
    def _collect_types(self, ast: Dict):
        """Collects all type declarations from AST"""
        if ast['type'] == 'Program':
            for decl in ast.get('declarations', []):
                if decl['type'] in ['Class', 'Interface', 'Struct']:
                    name = decl['name']
                    if name in self.types:
                        self.errors.append(f"Type {name} already defined")
                    else:
                        self.types[name] = TypeInfo(name)
                        
    def _validate_types(self):
        """Validate type relationships (inheritance, interfaces)"""
        for type_name, type_info in self.types.items():
            if type_info.parent and type_info.parent not in self.types:
                self.errors.append(f"Unknown parent type {type_info.parent} for {type_name}")
                
            for interface in type_info.interfaces:
                if interface not in self.types:
                    self.errors.append(f"Unknown interface {interface} for {type_name}")
                    
    def _analyze_declaration(self, decl: Dict):
        """Analyze a declaration"""
        if decl['type'] == 'Function':
            self._analyze_function(decl)
        elif decl['type'] == 'Class':
            self.current_class = decl['name']
            for method in decl.get('methods', []):
                self._analyze_method(method)
            for field in decl.get('fields', []):
                self._analyze_field(field)
            self.current_class = None
            
    def _analyze_method(self, method: Dict):
        """Analyze a method declaration"""
        if not self._is_valid_type(method['return_type']):
            self.errors.append(f"Invalid return type {method['return_type']} in method {method['name']}")
            
        for param in method.get('params', []):
            if not self._is_valid_type(param['type']):
                self.errors.append(f"Invalid parameter type {param['type']} in method {method['name']}")
                
        self._analyze_function(method)
        
    def _analyze_field(self, field: Dict):
        """Analyze a field declaration"""
        if not self._is_valid_type(field['type']):
            self.errors.append(f"Invalid field type {field['type']} for field {field['name']}")
            
    def _analyze_function(self, func: Dict):
        """Analyze a function declaration"""
        # Create new scope for function
        function_scope = Scope(func['name'], self.current_scope)
        self.current_scope.add_child(function_scope)
        old_scope = self.current_scope
        self.current_scope = function_scope
        
        # Add parameters to scope
        for param in func.get('params', []):
            symbol = Symbol(
                name=param['name'],
                type=SymbolType.VARIABLE,
                data_type=param['type'],
                scope=function_scope.name,
                location=(param.get('line', 0), param.get('column', 0))
            )
            if not function_scope.add_symbol(symbol):
                self.errors.append(f"Duplicate parameter name {param['name']}")
                
        # Analyze body
        if 'body' in func:
            self._analyze_statement(func['body'])
            
        self.current_scope = old_scope
        
    def _analyze_statement(self, stmt: Dict):
        """Analyze a statement"""
        if stmt['type'] == 'Block':
            # Create new scope for block
            block_scope = Scope(f"block{len(self.current_scope.children)}", self.current_scope)
            self.current_scope.add_child(block_scope)
            old_scope = self.current_scope
            self.current_scope = block_scope
            
            for s in stmt.get('statements', []):
                self._analyze_statement(s)
                
            self.current_scope = old_scope
            
        elif stmt['type'] == 'Return':
            expr_type = self._get_expression_type(stmt['value'])
            # TODO: Check return type matches function return type
            
        elif stmt['type'] == 'VarDecl':
            if not self._is_valid_type(stmt['var_type']):
                self.errors.append(f"Invalid variable type {stmt['var_type']}")
                
            init_type = self._get_expression_type(stmt['init'])
            if not self._are_types_compatible(init_type, stmt['var_type']):
                self.errors.append(f"Type mismatch in variable declaration: expected {stmt['var_type']}, got {init_type}")
                
            symbol = Symbol(
                name=stmt['name'],
                type=SymbolType.VARIABLE,
                data_type=stmt['var_type'],
                scope=self.current_scope.name,
                location=(stmt.get('line', 0), stmt.get('column', 0))
            )
            if not self.current_scope.add_symbol(symbol):
                self.errors.append(f"Variable {stmt['name']} already declared in this scope")
                
    def _get_expression_type(self, expr: Dict) -> str:
        """Get the type of an expression"""
        if expr['type'] == 'NumberLiteral':
            return 'i32'  # Default number type
        elif expr['type'] == 'StringLiteral':
            return 'string'
        elif expr['type'] == 'BoolLiteral':
            return 'bool'
        elif expr['type'] == 'Identifier':
            symbol = self.current_scope.lookup(expr['name'])
            if not symbol:
                self.errors.append(f"Undefined variable {expr['name']}")
                return 'unknown'
            return symbol.data_type
        elif expr['type'] == 'BinaryOp':
            left_type = self._get_expression_type(expr['left'])
            right_type = self._get_expression_type(expr['right'])
            # TODO: Implement proper type checking for operators
            return left_type
        return 'unknown'
        
    def _is_valid_type(self, type_name: str) -> bool:
        """Check if a type is valid"""
        return type_name in self.types
        
    def _are_types_compatible(self, source: str, target: str) -> bool:
        """Check if source type is compatible with target type"""
        if source == target:
            return True
        if source == 'unknown' or target == 'unknown':
            return True  # Be lenient with unknown types
        # TODO: Implement proper type compatibility checking
        return False
        
    def _check_unused_symbols(self):
        """Check for unused symbols"""
        def visit_scope(scope: Scope):
            for name, symbol in scope.symbols.items():
                if name not in self.used_symbols and not symbol.is_exported:
                    self.warnings.append(f"Symbol {name} is never used")
            for child in scope.children:
                visit_scope(child)
                
        visit_scope(self.global_scope)