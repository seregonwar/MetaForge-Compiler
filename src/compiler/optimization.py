# MetaForge Compiler - Optimization
#
# Copyright (c) 2025 SeregonWar (https://github.com/SeregonWar)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ---------------------------------------------------------------------------------
# Project: MetaForge Compiler
# Module: Optimization
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Handles optimization of the code.
#
# Key Features:
# - Passes for optimization
#
# Usage & Extensibility:
# This module is used by the compiler to optimize the generated code. To add a new optimization pass,
# create a new class that inherits from `OptimizationPass` and add it to the `optimization_passes` list.
#
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

from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import logging

from .ir_generator import IRInstruction

@dataclass
class BasicBlock:
    """A basic block of IR instructions"""
    instructions: List[IRInstruction]
    predecessors: Set[int]  # Block IDs
    successors: Set[int]   # Block IDs
    id: int

class IROptimizer:
    def __init__(self):
        self.blocks = []  # List of BasicBlock
        self.current_function = None
        
    def optimize(self, instructions: List[IRInstruction]) -> List[IRInstruction]:
        """Optimize IR instructions"""
        try:
            # Split into basic blocks
            self.blocks = self._build_cfg(instructions)
            
            # Run optimization passes
            changed = True
            while changed:
                changed = False
                changed |= self._constant_folding()
                changed |= self._dead_code_elimination()
                changed |= self._common_subexpression_elimination()
                
            # Merge blocks back into instruction list
            return self._flatten_cfg()
            
        except Exception as e:
            logging.error(f"IR optimization failed: {str(e)}")
            return instructions
            
    def _build_cfg(self, instructions: List[IRInstruction]) -> List[BasicBlock]:
        """Build control flow graph from instructions"""
        blocks = []
        current_block = []
        leaders = {0}  # First instruction is always a leader
        
        # Find basic block leaders
        for i, instr in enumerate(instructions):
            if instr.op == 'label':
                leaders.add(i)
            elif instr.op in ['jump', 'branch_false', 'return', 'return_void']:
                leaders.add(i + 1)
                
        # Split into basic blocks
        current_id = 0
        for i, instr in enumerate(instructions):
            if i in leaders and current_block:
                blocks.append(BasicBlock(current_block, set(), set(), current_id))
                current_id += 1
                current_block = []
            current_block.append(instr)
            
        if current_block:
            blocks.append(BasicBlock(current_block, set(), set(), current_id))
            
        # Add edges between blocks
        for i, block in enumerate(blocks):
            last = block.instructions[-1]
            
            if last.op == 'jump':
                target = self._find_label_block(blocks, last.args[0])
                if target is not None:
                    block.successors.add(target)
                    blocks[target].predecessors.add(i)
                    
            elif last.op == 'branch_false':
                # Fall through
                if i + 1 < len(blocks):
                    block.successors.add(i + 1)
                    blocks[i + 1].predecessors.add(i)
                    
                # Branch target
                target = self._find_label_block(blocks, last.args[1])
                if target is not None:
                    block.successors.add(target)
                    blocks[target].predecessors.add(i)
                    
            elif last.op not in ['return', 'return_void']:
                # Fall through
                if i + 1 < len(blocks):
                    block.successors.add(i + 1)
                    blocks[i + 1].predecessors.add(i)
                    
        return blocks
        
    def _constant_folding(self) -> bool:
        """Perform constant folding optimization"""
        changed = False
        
        for block in self.blocks:
            values = {}  # Variable -> constant value
            
            i = 0
            while i < len(block.instructions):
                instr = block.instructions[i]
                
                if instr.op == 'load_const' and instr.result:
                    values[instr.result] = float(instr.args[0])
                    i += 1
                    continue
                    
                # Try to fold binary operations
                if instr.op in ['add', 'sub', 'mul', 'div'] and instr.result:
                    left = values.get(instr.args[0])
                    right = values.get(instr.args[1])
                    
                    if left is not None and right is not None:
                        try:
                            if instr.op == 'add':
                                result = left + right
                            elif instr.op == 'sub':
                                result = left - right
                            elif instr.op == 'mul':
                                result = left * right
                            elif instr.op == 'div':
                                if right == 0:
                                    i += 1
                                    continue
                                result = left / right
                                
                            # Replace with constant
                            block.instructions[i] = IRInstruction('load_const', [str(result)], instr.result)
                            values[instr.result] = result
                            changed = True
                            
                        except Exception:
                            pass
                            
                i += 1
                
        return changed
        
    def _dead_code_elimination(self) -> bool:
        """Perform dead code elimination"""
        changed = False
        
        for block in self.blocks:
            used_vars = set()
            live_instructions = []
            
            # Scan backwards to find used variables
            for instr in reversed(block.instructions):
                keep = False
                
                # Instructions with side effects are always live
                if instr.op in ['store', 'call', 'return', 'return_void', 'branch_false', 'jump']:
                    keep = True
                    
                # Check if result is used
                if instr.result and instr.result in used_vars:
                    keep = True
                    
                if keep:
                    live_instructions.insert(0, instr)
                    # Add used variables
                    used_vars.update(arg for arg in instr.args if isinstance(arg, str) and not arg.startswith('L'))
                else:
                    changed = True
                    
            if len(live_instructions) != len(block.instructions):
                block.instructions = live_instructions
                
        return changed
        
    def _common_subexpression_elimination(self) -> bool:
        """Perform common subexpression elimination"""
        changed = False
        
        for block in self.blocks:
            expressions = {}  # (op, args) -> result
            
            i = 0
            while i < len(block.instructions):
                instr = block.instructions[i]
                
                # Only consider pure operations
                if instr.op in ['add', 'sub', 'mul', 'div', 'and', 'or', 'not', 'neg']:
                    key = (instr.op, tuple(instr.args))
                    
                    if key in expressions:
                        # Replace with existing result
                        block.instructions[i] = IRInstruction('load', [expressions[key]], instr.result)
                        changed = True
                    else:
                        expressions[key] = instr.result
                        
                i += 1
                
        return changed
        
    def _flatten_cfg(self) -> List[IRInstruction]:
        """Convert CFG back to linear instruction list"""
        instructions = []
        
        for block in self.blocks:
            instructions.extend(block.instructions)
            
        return instructions
        
    def _find_label_block(self, blocks: List[BasicBlock], label: str) -> Optional[int]:
        """Find block index containing given label"""
        for i, block in enumerate(blocks):
            if block.instructions and block.instructions[0].op == 'label' and block.instructions[0].args[0] == label:
                return i
        return None