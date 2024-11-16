from enum import Enum
from typing import Dict, List, Set
from dataclasses import dataclass

class OptimizationLevel(Enum):
    O0 = 0  # No optimization
    O1 = 1  # Basic optimizations 
    O2 = 2  # More aggressive optimizations
    O3 = 3  # Maximum optimizations
    Os = 4  # Optimize for size
    Oz = 5  # More size optimizations

@dataclass
class OptimizationPass:
    name: str
    level: OptimizationLevel
    enabled: bool = True
    applied: bool = False

class Optimizer:
    """Handles code optimizations"""
    
    def __init__(self, level: OptimizationLevel = OptimizationLevel.O0):
        self.level = level
        self.passes = self._init_passes()
        self.applied_passes: Set[str] = set()
        
    def _init_passes(self) -> List[OptimizationPass]:
        """Initialize optimization passes"""
        passes = [
            # Basic optimizations (O1)
            OptimizationPass("constant_folding", OptimizationLevel.O1),
            OptimizationPass("dead_code_elimination", OptimizationLevel.O1),
            OptimizationPass("common_subexpression_elimination", OptimizationLevel.O1),
            
            # Aggressive optimizations (O2)
            OptimizationPass("function_inlining", OptimizationLevel.O2),
            OptimizationPass("loop_unrolling", OptimizationLevel.O2),
            OptimizationPass("vectorization", OptimizationLevel.O2),
            
            # Maximum optimizations (O3)
            OptimizationPass("interprocedural_optimization", OptimizationLevel.O3),
            OptimizationPass("link_time_optimization", OptimizationLevel.O3),
            
            # Size optimizations (Os/Oz)
            OptimizationPass("code_size_reduction", OptimizationLevel.Os),
            OptimizationPass("aggressive_size_opts", OptimizationLevel.Oz)
        ]
        
        # Enable passes based on level
        for p in passes:
            p.enabled = p.level.value <= self.level.value
            
        return passes
        
    def optimize(self, ast: Dict) -> Dict:
        """Apply optimizations to the AST"""
        self.applied_passes.clear()
        
        for pass_ in self.passes:
            if pass_.enabled:
                try:
                    ast = self._run_pass(pass_, ast)
                    if pass_.applied:
                        self.applied_passes.add(pass_.name)
                except Exception as e:
                    print(f"Warning: optimization pass {pass_.name} failed: {str(e)}")
                    
        return ast
        
    def _run_pass(self, pass_: OptimizationPass, ast: Dict) -> Dict:
        """Execute a single optimization pass"""
        if pass_.name == "constant_folding":
            ast = self._constant_folding(ast)
            pass_.applied = True
        elif pass_.name == "dead_code_elimination":
            ast = self._dead_code_elimination(ast)
            pass_.applied = True
        elif pass_.name == "common_subexpression_elimination":
            ast = self._common_subexpression_elimination(ast)
            pass_.applied = True
        # ... other passes
        return ast
        
    def _constant_folding(self, ast: Dict) -> Dict:
        """Constant folding optimization"""
        def fold_constants(node):
            if isinstance(node, dict):
                if node.get('type') == 'BinaryOp':
                    # Get left and right operands
                    left = fold_constants(node.get('left'))
                    right = fold_constants(node.get('right'))
                    
                    # If both operands are literals, compute result
                    if left.get('type') == 'Literal' and right.get('type') == 'Literal':
                        op = node.get('operator')
                        try:
                            if op == '+':
                                result = left['value'] + right['value']
                            elif op == '-':
                                result = left['value'] - right['value']
                            elif op == '*':
                                result = left['value'] * right['value']
                            elif op == '/':
                                result = left['value'] / right['value']
                            return {'type': 'Literal', 'value': result}
                        except:
                            return node
                            
                # Recursively process all child nodes
                return {k: fold_constants(v) if isinstance(v, (dict, list)) else v 
                       for k, v in node.items()}
            elif isinstance(node, list):
                return [fold_constants(item) for item in node]
            return node
            
        return fold_constants(ast)
        
    def _dead_code_elimination(self, ast: Dict) -> Dict:
        """Dead code elimination"""
        def eliminate_dead_code(node):
            if isinstance(node, dict):
                if node.get('type') == 'If':
                    # Check if condition is a literal
                    condition = node.get('condition')
                    if condition and condition.get('type') == 'Literal':
                        # If condition is always true, keep only then branch
                        if condition['value']:
                            return node.get('then_branch')
                        # If condition is always false, keep only else branch
                        else:
                            return node.get('else_branch')
                            
                # Remove empty blocks
                if node.get('type') == 'Block':
                    statements = node.get('statements', [])
                    statements = [s for s in statements if s is not None]
                    if not statements:
                        return None
                    node['statements'] = statements
                    
                # Recursively process all child nodes
                return {k: eliminate_dead_code(v) if isinstance(v, (dict, list)) else v 
                       for k, v in node.items()}
            elif isinstance(node, list):
                nodes = [eliminate_dead_code(item) for item in node]
                return [n for n in nodes if n is not None]
            return node
            
        return eliminate_dead_code(ast)
        
    def _common_subexpression_elimination(self, ast: Dict) -> Dict:
        """Common subexpression elimination"""
        expressions = {}
        
        def eliminate_common_subexpressions(node):
            if isinstance(node, dict):
                if node.get('type') == 'BinaryOp':
                    # Create expression key
                    expr_key = (
                        node.get('operator'),
                        str(node.get('left')),
                        str(node.get('right'))
                    )
                    
                    # If expression seen before, reuse result
                    if expr_key in expressions:
                        return expressions[expr_key]
                        
                    # Otherwise compute and store result
                    expressions[expr_key] = node
                    
                # Recursively process all child nodes
                return {k: eliminate_common_subexpressions(v) if isinstance(v, (dict, list)) else v
                       for k, v in node.items()}
            elif isinstance(node, list):
                return [eliminate_common_subexpressions(item) for item in node]
            return node
            
        return eliminate_common_subexpressions(ast)