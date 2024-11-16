from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass

class Register(Enum):
    RAX = "rax"
    RBX = "rbx"
    RCX = "rcx"
    RDX = "rdx"
    RSI = "rsi"
    RDI = "rdi"
    RSP = "rsp"
    RBP = "rbp"
    R8  = "r8"
    R9  = "r9"
    R10 = "r10"
    R11 = "r11"
    R12 = "r12"
    R13 = "r13"
    R14 = "r14"
    R15 = "r15"

@dataclass
class Instruction:
    """Represents an x64 assembly instruction"""
    opcode: str
    operands: List[str]
    comment: Optional[str] = None

class X64Generator:
    """Generates x64 machine code directly"""
    
    def __init__(self):
        self.instructions: List[Instruction] = []
        self.data_section: List[str] = []
        self.string_literals: Dict[str, str] = {}
        self.current_function: Optional[str] = None
        self.label_counter: int = 0
        
    def generate_executable(self, ir: Dict) -> bytes:
        """Generates a PE executable file from IR"""
        # Reset state
        self.instructions.clear()
        self.data_section.clear()
        self.string_literals.clear()
        
        # Generate data section
        self._generate_data_section()
        
        # Generate code
        self._generate_code_section(ir)
        
        # Assemble everything into a PE file
        return self._assemble()
        
    def _generate_data_section(self):
        """Generates the .data section"""
        self.data_section.extend([
            "section .data",
            "    ; String literals"
        ])
        
    def _generate_code_section(self, ir: Dict):
        """Generates the .text section"""
        self.instructions.extend([
            Instruction("section", [".text"]),
            Instruction("global", ["main"])
        ])
        
        # Generate code for each function
        for func in ir['functions'].values():
            self._generate_function(func)
            
    def _generate_function(self, func: Dict):
        """Generates code for a function"""
        self.current_function = func['name']
        
        # Function prologue
        self.instructions.extend([
            Instruction(f"{func['name']}:", [], "Function entry"),
            Instruction("push", ["rbp"], "Save old base pointer"),
            Instruction("mov", ["rbp", "rsp"], "Set up new base pointer"),
            Instruction("sub", ["rsp", str(func['stack_size'])], "Allocate stack space")
        ])
        
        # Generate code for each block
        for block in func['blocks']:
            self._generate_block(block)
            
        # Function epilogue (if not already generated by ret)
        if not self.instructions[-1].opcode == "ret":
            self._generate_function_exit()
            
    def _generate_block(self, block: Dict):
        """Generates code for a basic block"""
        self.instructions.append(
            Instruction(f"{block['label']}:", [], "Basic block")
        )
        
        for instr in block['instructions']:
            self._generate_instruction(instr)
            
    def _generate_instruction(self, ir_instr: Dict):
        """Generates code for a single IR instruction"""
        opcode = ir_instr['opcode']
        
        if opcode == "load":
            self._generate_load(ir_instr)
        elif opcode == "store":
            self._generate_store(ir_instr)
        elif opcode == "add":
            self._generate_add(ir_instr)
        elif opcode == "call":
            self._generate_call(ir_instr)
        elif opcode == "ret":
            self._generate_return(ir_instr)
        # ... other opcodes
            
    def _generate_load(self, instr: Dict):
        """Generates code for load"""
        dst = self._get_register(instr['dest'])
        src = self._get_operand(instr['src'])
        
        self.instructions.append(
            Instruction("mov", [dst, src], "Load value")
        )
        
    def _generate_store(self, instr: Dict):
        """Generates code for store"""
        dst = self._get_operand(instr['dest'])
        src = self._get_register(instr['src'])
        
        self.instructions.append(
            Instruction("mov", [dst, src], "Store value")
        )
        
    def _generate_add(self, instr: Dict):
        """Generates code for add"""
        dst = self._get_register(instr['dest'])
        src1 = self._get_register(instr['src1'])
        src2 = self._get_operand(instr['src2'])
        
        self.instructions.extend([
            Instruction("mov", [dst, src1], "Setup add"),
            Instruction("add", [dst, src2], "Add values")
        ])
        
    def _generate_call(self, instr: Dict):
        """Generates code for function call"""
        # Save caller-saved registers
        self.instructions.extend([
            Instruction("push", [reg.value]) 
            for reg in [Register.RCX, Register.RDX, Register.R8, Register.R9]
        ])
        
        # Load arguments into registers
        for i, arg in enumerate(instr['args']):
            reg = [Register.RCX, Register.RDX, Register.R8, Register.R9][i]
            self.instructions.append(
                Instruction("mov", [reg.value, self._get_operand(arg)])
            )
            
        # Call
        self.instructions.append(
            Instruction("call", [instr['target']], "Call function")
        )
        
        # Restore registers
        self.instructions.extend([
            Instruction("pop", [reg.value])
            for reg in reversed([Register.RCX, Register.RDX, Register.R8, Register.R9])
        ])
        
    def _generate_return(self, instr: Dict):
        """Generates code for return"""
        if 'value' in instr:
            self.instructions.append(
                Instruction("mov", ["rax", self._get_operand(instr['value'])], 
                          "Set return value")
            )
            
        self._generate_function_exit()
        
    def _generate_function_exit(self):
        """Generates function epilogue"""
        self.instructions.extend([
            Instruction("mov", ["rsp", "rbp"], "Restore stack pointer"),
            Instruction("pop", ["rbp"], "Restore base pointer"),
            Instruction("ret", [], "Return from function")
        ])
        
    def _get_register(self, temp: str) -> str:
        """Maps a temporary to a register"""
        # Simple round-robin register allocation
        registers = [Register.R10, Register.R11, Register.R12, Register.R13, 
                    Register.R14, Register.R15]
        reg_index = hash(temp) % len(registers)
        return registers[reg_index].value
        
    def _get_operand(self, op: Dict) -> str:
        """Converts an IR operand to assembly"""
        if op['type'] == 'register':
            return self._get_register(op['value'])
        elif op['type'] == 'immediate':
            return str(op['value'])
        elif op['type'] == 'memory':
            return f"[rbp - {op['offset']}]"
        elif op['type'] == 'string':
            # Add string to data section if not already present
            if op['value'] not in self.string_literals:
                label = f"str_{len(self.string_literals)}"
                self.string_literals[op['value']] = label
                self.data_section.append(f'{label} db "{op["value"]}", 0')
            return self.string_literals[op['value']]
        else:
            raise ValueError(f"Unknown operand type: {op['type']}")
        
    def _assemble(self) -> bytes:
        """Assembles instructions into machine code"""
        # Generate assembly text
        asm = []
        
        # Add data section
        if self.data_section:
            asm.append("section .data")
            asm.extend(self.data_section)
            
        # Add code section
        asm.append("section .text")
        asm.append("global _start")
        
        # Add instructions
        for instr in self.instructions:
            if instr.comment:
                asm.append(f"; {instr.comment}")
            operands = ", ".join(instr.operands)
            asm.append(f"{instr.opcode} {operands}")
            
        # Use NASM to assemble
        with open("temp.asm", "w") as f:
            f.write("\n".join(asm))
            
        import subprocess
        subprocess.run(["nasm", "-f", "win64", "temp.asm", "-o", "temp.obj"])
        
        # Read object file
        with open("temp.obj", "rb") as f:
            return f.read()