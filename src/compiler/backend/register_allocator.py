from enum import Enum
from typing import Dict, Set, List, Optional
from dataclasses import dataclass
import networkx as nx

class Register(Enum):
    # Caller-saved registers
    RAX = "rax"  # Return value
    RCX = "rcx"  # First argument
    RDX = "rdx"  # Second argument
    R8  = "r8"   # Third argument
    R9  = "r9"   # Fourth argument
    R10 = "r10"  # Caller-saved
    R11 = "r11"  # Caller-saved
    
    # Callee-saved registers
    RBX = "rbx"
    RSI = "rsi"
    RDI = "rdi"
    R12 = "r12"
    R13 = "r13"
    R14 = "r14"
    R15 = "r15"
    
    # Special registers
    RSP = "rsp"  # Stack pointer
    RBP = "rbp"  # Base pointer

@dataclass
class LiveRange:
    start: int  # Instruction index where variable becomes live
    end: int    # Instruction index where variable dies
    temp: str   # Temporary variable name
    reg: Optional[Register] = None  # Allocated register
    spill: bool = False  # True if variable is spilled to memory

class RegisterAllocator:
    def __init__(self):
        self.live_ranges: List[LiveRange] = []
        self.interference_graph = nx.Graph()
        self.coloring: Dict[str, Register] = {}
        self.spilled_vars: Set[str] = set()
        
        # Available registers for allocation
        self.available_regs = [
            Register.RAX, Register.RCX, Register.RDX,
            Register.R8, Register.R9, Register.R10, Register.R11,
            Register.RBX, Register.RSI, Register.RDI,
            Register.R12, Register.R13, Register.R14, Register.R15
        ]
        
    def allocate_registers(self, ir_function: Dict) -> Dict[str, Register]:
        """Allocates registers for a function using graph coloring"""
        
        # Calculate live ranges
        self._compute_live_ranges(ir_function)
        
        # Build interference graph
        self._build_interference_graph()
        
        # Color the graph
        self._color_graph()
        
        # Handle spilled variables
        if self.spilled_vars:
            self._handle_spills(ir_function)
            
        return self.coloring
        
    def _compute_live_ranges(self, ir_function: Dict):
        """Computes live ranges for each variable"""
        self.live_ranges.clear()
        
        # Liveness analysis for each block
        for block in ir_function['blocks']:
            live_vars = set()  # Variables live at end of block
            
            # Analyze instructions in reverse order
            for i, instr in enumerate(reversed(block['instructions'])):
                curr_idx = len(block['instructions']) - i - 1
                
                # Add definitions
                if 'dest' in instr:
                    live_range = LiveRange(
                        start=curr_idx,
                        end=curr_idx,
                        temp=instr['dest']
                    )
                    self.live_ranges.append(live_range)
                    live_vars.discard(instr['dest'])
                    
                # Add uses
                for op in ['src1', 'src2']:
                    if op in instr and isinstance(instr[op], str):
                        live_vars.add(instr[op])
                        # Extend existing live range or create new one
                        found = False
                        for lr in self.live_ranges:
                            if lr.temp == instr[op]:
                                lr.start = min(lr.start, curr_idx)
                                lr.end = max(lr.end, curr_idx)
                                found = True
                                break
                        if not found:
                            self.live_ranges.append(LiveRange(
                                start=curr_idx,
                                end=curr_idx,
                                temp=instr[op]
                            ))
                            
    def _build_interference_graph(self):
        """Builds the interference graph"""
        self.interference_graph.clear()
        
        # Add nodes for each variable
        for lr in self.live_ranges:
            self.interference_graph.add_node(lr.temp)
            
        # Add edges for overlapping live ranges
        for i, lr1 in enumerate(self.live_ranges):
            for lr2 in self.live_ranges[i+1:]:
                if (lr1.start <= lr2.end and lr2.start <= lr1.end):
                    self.interference_graph.add_edge(lr1.temp, lr2.temp)
                    
    def _color_graph(self):
        """Colors the graph using Chaitin's algorithm"""
        self.coloring.clear()
        self.spilled_vars.clear()
        
        # Stack for coloring
        stack = []
        graph = self.interference_graph.copy()
        
        # Simplification: remove nodes with degree < number of registers
        while graph:
            spill_candidate = None
            min_degree = float('inf')
            
            for node in graph.nodes():
                degree = graph.degree(node)
                if degree < len(self.available_regs):
                    stack.append((node, set(graph.neighbors(node))))
                    graph.remove_node(node)
                    break
                elif degree < min_degree:
                    spill_candidate = node
                    min_degree = degree
            else:
                if spill_candidate:
                    self.spilled_vars.add(spill_candidate)
                    graph.remove_node(spill_candidate)
                else:
                    break
                    
        # Color the nodes
        used_colors = set()
        while stack:
            node, neighbors = stack.pop()
            
            # Find first available color
            used_colors.clear()
            for neighbor in neighbors:
                if neighbor in self.coloring:
                    used_colors.add(self.coloring[neighbor])
                    
            for reg in self.available_regs:
                if reg not in used_colors:
                    self.coloring[node] = reg
                    break
            else:
                self.spilled_vars.add(node)
                
    def _handle_spills(self, ir_function: Dict):
        """Handles spilled variables by allocating stack space"""
        stack_offset = 0
        spill_locations = {}
        
        # Allocate stack space for each spilled variable
        for var in self.spilled_vars:
            stack_offset += 8  # Assumes 8-byte variables
            spill_locations[var] = stack_offset
            
        # Update instructions to use stack instead of registers
        for block in ir_function['blocks']:
            new_instructions = []
            
            for instr in block['instructions']:
                if 'dest' in instr and instr['dest'] in self.spilled_vars:
                    # Store result to stack
                    new_instructions.append({
                        'opcode': 'mov',
                        'dest': f'[rbp-{spill_locations[instr["dest"]]}]',
                        'src': Register.RAX.value
                    })
                    
                for op in ['src1', 'src2']:
                    if op in instr and instr[op] in self.spilled_vars:
                        # Load from stack to temporary register
                        new_instructions.append({
                            'opcode': 'mov',
                            'dest': Register.R11.value,
                            'src': f'[rbp-{spill_locations[instr[op]]}]'
                        })
                        instr[op] = Register.R11.value
                        
                new_instructions.append(instr)
                
            block['instructions'] = new_instructions
            
        # Update stack frame size
        ir_function['stack_size'] = max(ir_function['stack_size'], stack_offset)