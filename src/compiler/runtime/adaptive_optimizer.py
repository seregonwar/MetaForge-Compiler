from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import time
import logging
import ast

@dataclass
class ExecutionProfile:
    call_count: int = 0
    total_time: float = 0
    avg_time: float = 0
    input_sizes: List[int] = None
    complexity_class: Optional[str] = None
    
    def update(self, execution_time: float, input_size: Optional[int] = None):
        self.call_count += 1
        self.total_time += execution_time
        self.avg_time = self.total_time / self.call_count
        
        if input_size is not None:
            if self.input_sizes is None:
                self.input_sizes = []
            self.input_sizes.append(input_size)
            self._analyze_complexity()
            
    def _analyze_complexity(self):
        """Analyze time complexity based on input sizes and execution times"""
        if len(self.input_sizes) < 2:
            return
            
        # Calculate growth rate
        x = self.input_sizes[-2:]  # Last two input sizes
        y = [self.avg_time * 1000] * 2  # Convert to ms
        
        ratio = (y[1]/y[0]) / (x[1]/x[0])
        
        # Classify complexity
        if ratio <= 1.1:  # Allow some margin for O(n)
            self.complexity_class = "O(n)"
        elif ratio <= 2:
            self.complexity_class = "O(n log n)"
        elif ratio <= 4:
            self.complexity_class = "O(n²)"
        else:
            self.complexity_class = "O(n³) or worse"

class OptimizationPattern:
    def __init__(self, name: str, pattern: str, replacement: str, condition: str = None):
        self.name = name
        self.pattern = pattern  # AST pattern to match
        self.replacement = replacement  # Optimized version
        self.condition = condition  # When to apply
        
class AdaptiveOptimizer:
    def __init__(self):
        self.profiles: Dict[str, ExecutionProfile] = {}
        self.patterns: List[OptimizationPattern] = []
        self._init_patterns()
        
    def _init_patterns(self):
        """Initialize common optimization patterns"""
        # List comprehension instead of explicit loops
        self.patterns.append(OptimizationPattern(
            "list_comprehension",
            """
            result = []
            for x in iterable:
                if condition:
                    result.append(expression)
            """,
            "result = [expression for x in iterable if condition]"
        ))
        
        # Dict comprehension for transformations
        self.patterns.append(OptimizationPattern(
            "dict_comprehension",
            """
            result = {}
            for k, v in items:
                result[k] = transform(v)
            """,
            "result = {k: transform(v) for k, v in items}"
        ))
        
        # Use set for O(1) lookup
        self.patterns.append(OptimizationPattern(
            "set_lookup",
            """
            found = False
            for item in collection:
                if item == target:
                    found = True
                    break
            """,
            "found = target in set(collection)",
            "len(collection) > 100"  # Only worth it for large collections
        ))
        
    def start_profile(self, func_name: str):
        """Start profiling a function execution"""
        if func_name not in self.profiles:
            self.profiles[func_name] = ExecutionProfile()
        return time.time()
        
    def end_profile(self, func_name: str, start_time: float, input_size: Optional[int] = None):
        """End profiling a function execution"""
        duration = time.time() - start_time
        self.profiles[func_name].update(duration, input_size)
        
        # Log if function is inefficient
        profile = self.profiles[func_name]
        if profile.complexity_class and profile.complexity_class.startswith("O(n²)"):
            logging.warning(
                f"Function {func_name} has {profile.complexity_class} complexity. "
                f"Consider optimizing for better performance."
            )
            
    def optimize_ast(self, node: ast.AST) -> ast.AST:
        """Apply optimization patterns to AST"""
        if isinstance(node, ast.For):
            # Try to convert to list/dict comprehension
            if self._is_building_list(node):
                return self._convert_to_list_comp(node)
            elif self._is_building_dict(node):
                return self._convert_to_dict_comp(node)
                
        elif isinstance(node, ast.While):
            # Try to optimize search patterns
            if self._is_search_pattern(node):
                return self._optimize_search(node)
                
        # Recursively process children
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, ast.AST):
                        value[i] = self.optimize_ast(item)
            elif isinstance(value, ast.AST):
                setattr(node, field, self.optimize_ast(value))
                
        return node
        
    def _is_building_list(self, node: ast.For) -> bool:
        """Check if for loop is building a list"""
        return (
            isinstance(node.body[-1], ast.Expr) and
            isinstance(node.body[-1].value, ast.Call) and
            isinstance(node.body[-1].value.func, ast.Attribute) and
            node.body[-1].value.func.attr == 'append'
        )
        
    def _is_building_dict(self, node: ast.For) -> bool:
        """Check if for loop is building a dictionary"""
        return (
            isinstance(node.body[-1], ast.Assign) and
            isinstance(node.body[-1].targets[0], ast.Subscript)
        )
        
    def _is_search_pattern(self, node: ast.While) -> bool:
        """Check if while loop is a search pattern"""
        return (
            isinstance(node.test, ast.Compare) and
            any(isinstance(op, (ast.Eq, ast.NotEq)) for op in node.test.ops)
        )
        
    def _convert_to_list_comp(self, node: ast.For) -> ast.ListComp:
        """Convert for loop to list comprehension"""
        elt = node.body[-1].value.args[0]  # Expression being appended
        
        # Extract filter condition if present
        if len(node.body) > 1 and isinstance(node.body[0], ast.If):
            condition = node.body[0].test
        else:
            condition = None
            
        generators = [
            ast.comprehension(
                target=node.target,
                iter=node.iter,
                ifs=[condition] if condition else [],
                is_async=0
            )
        ]
        
        return ast.ListComp(elt=elt, generators=generators)
        
    def _convert_to_dict_comp(self, node: ast.For) -> ast.DictComp:
        """Convert for loop to dictionary comprehension"""
        assign = node.body[-1]
        key = assign.targets[0].slice
        value = assign.value
        
        generators = [
            ast.comprehension(
                target=node.target,
                iter=node.iter,
                ifs=[],
                is_async=0
            )
        ]
        
        return ast.DictComp(key=key, value=value, generators=generators)
        
    def _optimize_search(self, node: ast.While) -> ast.If:
        """Convert search loop to set membership test"""
        # Create set from collection being searched
        collection = node.test.comparators[0]
        target = node.test.left
        
        return ast.If(
            test=ast.Call(
                func=ast.Name(id='any', ctx=ast.Load()),
                args=[
                    ast.GeneratorExp(
                        elt=ast.Compare(
                            left=ast.Name(id='x', ctx=ast.Load()),
                            ops=[ast.Eq()],
                            comparators=[target]
                        ),
                        generators=[
                            ast.comprehension(
                                target=ast.Name(id='x', ctx=ast.Store()),
                                iter=collection,
                                ifs=[],
                                is_async=0
                            )
                        ]
                    )
                ],
                keywords=[]
            ),
            body=node.body,
            orelse=[]
        )
        
    def get_optimization_report(self) -> str:
        """Generate optimization report"""
        report = ["Optimization Report:"]
        
        for func_name, profile in self.profiles.items():
            report.append(f"\nFunction: {func_name}")
            report.append(f"  Calls: {profile.call_count}")
            report.append(f"  Avg Time: {profile.avg_time*1000:.2f}ms")
            if profile.complexity_class:
                report.append(f"  Complexity: {profile.complexity_class}")
                
        return "\n".join(report)
