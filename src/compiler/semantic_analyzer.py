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

class SemanticAnalyzer:
    def __init__(self):
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.used_symbols: Set[str] = set()
        
    def _all_scopes(self) -> Iterator[Scope]:
        """Iterates over all scopes in DFS order"""
        def visit_scope(scope: Scope):
            yield scope
            for child in scope.children:
                yield from visit_scope(child)
                
        yield from visit_scope(self.global_scope)
        
    def analyze(self, ast: Dict) -> bool:
        """Performs complete semantic analysis"""
        try:
            # First pass: symbol collection
            self._collect_symbols(ast)
            
            # Second pass: type checking
            self._check_types(ast)
            
            # Third pass: flow analysis
            self._analyze_control_flow(ast)
            
            # Fourth pass: additional checks
            self._check_unused_symbols()
            self._check_circular_dependencies()
            self._validate_exports()
            
            return len(self.errors) == 0
            
        except Exception as e:
            self.errors.append(f"Fatal semantic error: {str(e)}")
            return False
            
    def _collect_symbols(self, node: Dict, scope: str = "global"):
        """Collects all symbols defined in the code"""
        if node['type'] == 'Program':
            for decl in node['declarations']:
                self._collect_symbols(decl, scope)
                
        elif node['type'] == 'Function':
            # Add function to current scope
            symbol = Symbol(
                name=node['name'],
                type=SymbolType.FUNCTION,
                data_type=node['return_type'],
                scope=scope,
                location=(node.get('line', 0), node.get('column', 0)),
                is_exported=node.get('exported', False)
            )
            
            if not self.current_scope.add_symbol(symbol):
                self.errors.append(f"Symbol {node['name']} already defined in scope {scope}")
                return
                
            # Create new scope for function body
            function_scope = Scope(f"{scope}.{node['name']}", self.current_scope)
            self.current_scope.add_child(function_scope)
            
            # Analyze parameters
            old_scope = self.current_scope
            self.current_scope = function_scope
            
            for param in node.get('params', []):
                self._collect_symbols(param, function_scope.name)
                
            # Analyze body
            if 'body' in node:
                self._collect_symbols(node['body'], function_scope.name)
                
            self.current_scope = old_scope
                
        elif node['type'] == 'Block':
            # Create new scope for block
            block_scope = Scope(f"{scope}.block{len(self.current_scope.children)}", self.current_scope)
            self.current_scope.add_child(block_scope)
            
            old_scope = self.current_scope
            self.current_scope = block_scope
            
            for stmt in node.get('statements', []):
                self._collect_symbols(stmt, block_scope.name)
                
            self.current_scope = old_scope
            
        elif node['type'] == 'Import':
            # Imports don't define local symbols
            pass
            
    def _check_types(self, node: Dict):
        """Verifies type correctness"""
        if node['type'] == 'Program':
            for decl in node['declarations']:
                self._check_types(decl)
                
        elif node['type'] == 'Function':
            # Check return type
            if node['return_type'] not in {'i32', 'void'}:  # Currently only support these
                self.errors.append(f"Invalid return type: {node['return_type']}")
                
            # Check body
            if 'body' in node:
                self._check_types(node['body'])
                
        elif node['type'] == 'FunctionCall':
            # Verify function exists
            symbol = self.current_scope.lookup(node['name'])
            if not symbol or symbol.type != SymbolType.FUNCTION:
                self.errors.append(f"Undefined function: {node['name']}")
            else:
                self.used_symbols.add(node['name'])
                
        elif node['type'] == 'Return':
            # Check return value type
            if node['value']['type'] == 'NumberLiteral':
                # Currently assume integer literals are i32
                pass
            else:
                self.errors.append(f"Unsupported return type: {node['value']['type']}")
                
    def _analyze_control_flow(self, node: Dict):
        """Analyzes control flow"""
        if node['type'] == 'Function':
            # Verify all paths return a value
            if not self._has_return_path(node['body']):
                self.warnings.append(f"Function {node['name']} may not return a value in all paths")
                
    def _has_return_path(self, node: Dict) -> bool:
        """Checks if a node has a path ending in return"""
        if node['type'] == 'Return':
            return True
            
        elif node['type'] == 'Block':
            for stmt in node.get('statements', []):
                if self._has_return_path(stmt):
                    return True
        return False
        
    def _check_unused_symbols(self):
        """Checks for unused symbols"""
        for scope in self._all_scopes():
            for name, symbol in scope.symbols.items():
                if name not in self.used_symbols and not symbol.is_exported:
                    self.warnings.append(f"Symbol {name} is never used")
                    
    def _check_circular_dependencies(self):
        """Checks for circular dependencies"""
        visited = set()
        path = []
        
        def visit(symbol: Symbol):
            if symbol.name in path:
                cycle = ' -> '.join(path[path.index(symbol.name):] + [symbol.name])
                self.errors.append(f"Circular dependency detected: {cycle}")
                return
                
            if symbol.name in visited:
                return
                
            visited.add(symbol.name)
            path.append(symbol.name)
            
            for ref in (symbol.references or []):
                visit(ref)
                
            path.pop()
            
        for symbol in self.global_scope.symbols.values():
            visit(symbol)
            
    def _validate_exports(self):
        """Validates exports"""
        for symbol in self.global_scope.symbols.values():
            if symbol.is_exported:
                # Verify exported types are complete
                if symbol.type == SymbolType.STRUCT:
                    self._check_exported_struct(symbol)
                    
                # Verify exported functions use only public types
                elif symbol.type == SymbolType.FUNCTION:
                    self._check_exported_function(symbol)
                    
    def _get_expression_type(self, node: Dict) -> str:
        """Determines expression type"""
        if node['type'] == 'Literal':
            return self._get_literal_type(node['value'])
        elif node['type'] == 'Identifier':
            symbol = self.current_scope.lookup(node['name'])
            return symbol.data_type if symbol else 'unknown'
        elif node['type'] == 'BinaryOp':
            return self._get_operation_type(node)
        return 'unknown'
        
    def _are_types_compatible(self, type1: str, type2: str, operation: str) -> bool:
        """Verifies type compatibility"""
        # Basic type compatibility rules
        if type1 == type2:
            return True
            
        # Numeric type conversions
        numeric_types = {'i32', 'i64', 'f32', 'f64'}
        if type1 in numeric_types and type2 in numeric_types:
            return True
            
        return False
        
    def _check_return_paths(self, node: Dict) -> bool:
        """Verifies all paths return a value"""
        if node['type'] == 'Return':
            return True
            
        elif node['type'] == 'Block':
            has_return = False
            for stmt in node.get('statements', []):
                has_return = has_return or self._check_return_paths(stmt)
            return has_return
            
        elif node['type'] == 'If':
            # Both branches must return
            return (self._check_return_paths(node['then']) and 
                   self._check_return_paths(node['else']))
                   
        return False
        
    def _has_break_condition(self, node: Dict) -> bool:
        """Checks loop exit conditions"""
        if node['type'] == 'Break':
            return True
            
        elif node['type'] == 'Block':
            for stmt in node.get('statements', []):
                if self._has_break_condition(stmt):
                    return True
                    
        elif node['type'] == 'If':
            return (self._has_break_condition(node['then']) or
                   self._has_break_condition(node['else']))
                   
        return False