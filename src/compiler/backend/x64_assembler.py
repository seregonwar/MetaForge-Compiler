from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Union, Set
import struct

class Register(Enum):
    # General purpose registers
    RAX = 0
    RCX = 1
    RDX = 2
    RBX = 3
    RSP = 4
    RBP = 5
    RSI = 6
    RDI = 7
    R8  = 8
    R9  = 9
    R10 = 10
    R11 = 11
    R12 = 12
    R13 = 13
    R14 = 14
    R15 = 15

class OperandType(Enum):
    REGISTER = "reg"
    MEMORY = "mem"
    IMMEDIATE = "imm"
    LABEL = "label"

@dataclass
class Operand:
    type: OperandType
    value: Union[Register, int, str]
    size: int = 8  # Default 64-bit
    base: Optional[Register] = None
    index: Optional[Register] = None
    scale: int = 1
    displacement: int = 0

class X64Assembler:
    """Assembles x64 machine code directly"""
    
    def __init__(self):
        self.code: bytearray = bytearray()
        self.labels: Dict[str, int] = {}
        self.fixups: List[tuple[int, str]] = []  # [(offset, label), ...]
        self.external_symbols: Set[str] = set()  # External symbols (e.g. printf)
        
    def assemble(self, instructions: List[Dict]) -> bytes:
        """Assembles a list of instructions into machine code"""
        self.code.clear()
        self.labels.clear()
        self.fixups.clear()
        self.external_symbols.clear()
        
        # First pass: collect labels
        offset = 0
        for instr in instructions:
            if 'label' in instr:
                self.labels[instr['label']] = offset
            else:
                offset += self._get_instruction_size(instr)
                
        # Second pass: generate code
        for instr in instructions:
            if 'label' not in instr:
                self._assemble_instruction(instr)
                
        # Apply fixups
        self._apply_fixups()
        
        return bytes(self.code)
        
    def _get_instruction_size(self, instr: Dict) -> int:
        """Calculates the size of an instruction"""
        opcode = instr['opcode']
        operands = instr.get('operands', [])
        
        if opcode == 'mov':
            return self._get_mov_size(operands)
        elif opcode == 'push':
            return self._get_push_size(operands)
        elif opcode == 'pop':
            return self._get_pop_size(operands)
        elif opcode == 'call':
            return self._get_call_size(instr)
        elif opcode == 'ret':
            return 1  # C3
        elif opcode in ['add', 'sub', 'and', 'or', 'xor']:
            return self._get_alu_size(operands)
        elif opcode == 'lea':
            return self._get_lea_size(operands)
            
        return 0  # Unknown instruction
        
    def _get_mov_size(self, operands: List[str]) -> int:
        """Calculates the size of a MOV instruction"""
        if len(operands) != 2:
            return 0
            
        dst = self._parse_operand(operands[0])
        src = self._parse_operand(operands[1])
        size = 0
        
        # REX prefix if needed
        if self._needs_rex(dst) or self._needs_rex(src):
            size += 1
            
        # Base opcode
        size += 1
        
        # ModRM
        size += 1
        
        # SIB if needed
        if self._needs_sib(dst) or self._needs_sib(src):
            size += 1
            
        # Displacement
        if dst.displacement or src.displacement:
            if -128 <= (dst.displacement or src.displacement) <= 127:
                size += 1
            else:
                size += 4
                
        # Immediate
        if src.type == OperandType.IMMEDIATE:
            if -128 <= src.value <= 127:
                size += 1
            else:
                size += 4 if dst.size == 4 else 8
                
        return size
        
    def _get_push_size(self, operands: List[str]) -> int:
        """Calculates the size of a PUSH instruction"""
        if not operands:
            return 0
            
        op = self._parse_operand(operands[0])
        size = 1  # Base opcode
        
        # REX prefix if needed
        if self._needs_rex(op):
            size += 1
            
        return size
        
    def _get_pop_size(self, operands: List[str]) -> int:
        """Calculates the size of a POP instruction"""
        if not operands:
            return 0
            
        op = self._parse_operand(operands[0])
        size = 1  # Base opcode
        
        # REX prefix if needed
        if self._needs_rex(op):
            size += 1
            
        return size
        
    def _get_call_size(self, instr: Dict) -> int:
        """Calculates the size of a CALL instruction"""
        if 'target' in instr:
            return 5  # E8 + rel32
        elif instr.get('operands'):
            op = self._parse_operand(instr['operands'][0])
            if op.type == OperandType.REGISTER:
                return 2  # FF /2
            else:
                return 6  # FF /2 + displacement
        return 0
        
    def _get_alu_size(self, operands: List[str]) -> int:
        """Calculates the size of an ALU instruction"""
        if len(operands) != 2:
            return 0
            
        dst = self._parse_operand(operands[0])
        src = self._parse_operand(operands[1])
        size = 0
        
        # REX prefix if needed
        if self._needs_rex(dst) or self._needs_rex(src):
            size += 1
            
        # Base opcode
        size += 1
        
        # ModRM
        size += 1
        
        # Immediate/displacement
        if src.type == OperandType.IMMEDIATE:
            if -128 <= src.value <= 127:
                size += 1
            else:
                size += 4
                
        return size
        
    def _get_lea_size(self, operands: List[str]) -> int:
        """Calculates the size of a LEA instruction"""
        if len(operands) != 2:
            return 0
            
        dst = self._parse_operand(operands[0])
        src = self._parse_operand(operands[1])
        size = 0
        
        # REX prefix if needed
        if self._needs_rex(dst) or self._needs_rex(src):
            size += 1
            
        # Opcode
        size += 1
        
        # ModRM
        size += 1
        
        # SIB if needed
        if self._needs_sib(src):
            size += 1
            
        # Displacement
        if src.displacement:
            if -128 <= src.displacement <= 127:
                size += 1
            else:
                size += 4
                
        return size
        
    def _assemble_instruction(self, instr: Dict):
        """Assembles a single instruction"""
        opcode = instr['opcode']
        operands = instr.get('operands', [])
        
        if opcode == 'mov':
            self._assemble_mov(operands[0], operands[1])
        elif opcode == 'push':
            self._assemble_push(operands[0])
        elif opcode == 'pop':
            self._assemble_pop(operands[0])
        elif opcode == 'call':
            if 'target' in instr:
                self._assemble_call_external(instr['target'])
            elif operands:
                self._assemble_call(operands[0])
            else:
                raise ValueError("Call instruction missing target")
        elif opcode == 'ret':
            self._assemble_ret()
        elif opcode == 'sub':
            self._assemble_sub(operands[0], operands[1])
        elif opcode == 'lea':
            self._assemble_lea(operands[0], operands[1])
            
    def _assemble_mov(self, dst: str, src: str):
        """Assembles MOV instruction"""
        dst_op = self._parse_operand(dst)
        src_op = self._parse_operand(src)
        
        # REX prefix if needed
        if self._needs_rex(dst_op) or self._needs_rex(src_op):
            self.code.append(0x48)
            
        # Reg -> Reg
        if dst_op.type == OperandType.REGISTER and src_op.type == OperandType.REGISTER:
            self.code.append(0x89)  # MOV r/m64, r64
            self.code.append(0xC0 | (src_op.value.value << 3) | dst_op.value.value)
            
        # Imm -> Reg
        elif dst_op.type == OperandType.REGISTER and src_op.type == OperandType.IMMEDIATE:
            self.code.append(0xB8 + dst_op.value.value)  # MOV reg, imm
            self._emit_immediate(src_op.value, dst_op.size)
            
        # Mem -> Reg
        elif dst_op.type == OperandType.REGISTER and src_op.type == OperandType.MEMORY:
            self.code.append(0x8B)  # MOV r64, r/m64
            self._emit_modrm_sib(src_op, dst_op.value)
            
        # Reg -> Mem
        elif dst_op.type == OperandType.MEMORY and src_op.type == OperandType.REGISTER:
            self.code.append(0x89)  # MOV r/m64, r64
            self._emit_modrm_sib(dst_op, src_op.value)
            
    def _assemble_push(self, operand: str):
        """Assembles PUSH instruction"""
        op = self._parse_operand(operand)
        if op.type == OperandType.REGISTER:
            # REX prefix if needed
            if self._needs_rex(op):
                self.code.append(0x41)
            self.code.append(0x50 + op.value.value)  # PUSH r64
            
    def _assemble_pop(self, operand: str):
        """Assembles POP instruction"""
        op = self._parse_operand(operand)
        if op.type == OperandType.REGISTER:
            # REX prefix if needed
            if self._needs_rex(op):
                self.code.append(0x41)
            self.code.append(0x58 + op.value.value)  # POP r64
            
    def _assemble_call_external(self, target: str):
        """Assembles external function call"""
        self.code.append(0xE8)  # CALL rel32
        self.external_symbols.add(target)
        self.fixups.append((len(self.code), target))
        self.code.extend(b'\0\0\0\0')  # Placeholder for rel32
        
    def _assemble_call(self, target: str):
        """Assembles internal function call"""
        op = self._parse_operand(target)
        if op.type == OperandType.LABEL:
            self.code.append(0xE8)  # CALL rel32
            if op.value in self.labels:
                rel32 = self.labels[op.value] - (len(self.code) + 4)
                self.code.extend(struct.pack('<i', rel32))
            else:
                self.fixups.append((len(self.code), op.value))
                self.code.extend(b'\0\0\0\0')
        else:
            # Indirect call through register
            self.code.append(0xFF)  # CALL r/m64
            self.code.append(0xD0 | op.value.value)
            
    def _assemble_ret(self):
        """Assembles RET instruction"""
        self.code.append(0xC3)
        
    def _assemble_sub(self, dst: str, src: Union[str, int]):
        """Assembles SUB instruction"""
        dst_op = self._parse_operand(dst)
        src_op = self._parse_operand(src)
        
        # REX prefix if needed
        if self._needs_rex(dst_op) or self._needs_rex(src_op):
            self.code.append(0x48)
            
        if dst_op.type == OperandType.REGISTER and src_op.type == OperandType.IMMEDIATE:
            if -128 <= src_op.value <= 127:
                self.code.append(0x83)  # SUB r/m64, imm8
                self.code.append(0xE8 + dst_op.value.value)
                self.code.append(src_op.value & 0xFF)
            else:
                self.code.append(0x81)  # SUB r/m64, imm32
                self.code.append(0xE8 + dst_op.value.value)
                self._emit_immediate(src_op.value, 4)
                
    def _assemble_lea(self, dst: str, src: str):
        """Assembles LEA instruction"""
        dst_op = self._parse_operand(dst)
        src_op = self._parse_operand(src)
        
        # REX prefix if needed
        if self._needs_rex(dst_op) or self._needs_rex(src_op):
            self.code.append(0x48)
            
        self.code.append(0x8D)  # LEA r64, m
        self._emit_modrm_sib(src_op, dst_op.value)
        
    def _parse_operand(self, op: Union[str, int]) -> Operand:
        """Converts operand to standard format"""
        if isinstance(op, str):
            try:
                reg = Register[op.upper()]
                return Operand(OperandType.REGISTER, reg)
            except KeyError:
                return Operand(OperandType.LABEL, op)
        elif isinstance(op, int):
            return Operand(OperandType.IMMEDIATE, op)
        elif isinstance(op, Operand):
            return op
        raise ValueError(f"Invalid operand: {op}")
        
    def _needs_rex(self, op: Operand) -> bool:
        """Checks if REX prefix is needed"""
        if op.type == OperandType.REGISTER:
            return isinstance(op.value, Register) and op.value.value >= 8
        elif op.type == OperandType.MEMORY:
            return ((op.base and op.base.value >= 8) or
                   (op.index and op.index.value >= 8))
        return False
        
    def _needs_sib(self, op: Operand) -> bool:
        """Checks if SIB byte is needed"""
        return (op.type == OperandType.MEMORY and
                (op.index is not None or
                 op.base == Register.RSP))
                 
    def _emit_immediate(self, value: int, size: int):
        """Emits an immediate value"""
        if size == 1:
            self.code.append(value & 0xFF)
        elif size == 2:
            self.code.extend(struct.pack('<H', value & 0xFFFF))
        elif size == 4:
            self.code.extend(struct.pack('<I', value & 0xFFFFFFFF))
        elif size == 8:
            self.code.extend(struct.pack('<Q', value))
            
    def _emit_modrm_sib(self, mem: Operand, reg: Register):
        """Emits ModRM and SIB bytes"""
        if not mem.base and not mem.index:
            # Absolute address
            self.code.append(0x00 | (reg.value << 3) | 0x04)
            self.code.append(0x25)  # SIB: no base, no index
            self._emit_immediate(mem.displacement, 4)
            
        elif not mem.index:
            # Base only
            if mem.displacement == 0:
                self.code.append(0x00 | (reg.value << 3) | mem.base.value)
            elif -128 <= mem.displacement <= 127:
                self.code.append(0x40 | (reg.value << 3) | mem.base.value)
                self.code.append(mem.displacement & 0xFF)
            else:
                self.code.append(0x80 | (reg.value << 3) | mem.base.value)
                self._emit_immediate(mem.displacement, 4)
                
        else:
            # Base + index
            self.code.append(0x04 | (reg.value << 3))  # ModRM with SIB
            
            # SIB byte
            scale_bits = {1: 0, 2: 1, 4: 2, 8: 3}[mem.scale]
            self.code.append((scale_bits << 6) | (mem.index.value << 3) | 
                           (mem.base.value if mem.base else 5))
                           
            if mem.displacement or not mem.base:
                if not mem.base:
                    self._emit_immediate(mem.displacement, 4)
                elif -128 <= mem.displacement <= 127:
                    self.code.append(mem.displacement & 0xFF)
                else:
                    self._emit_immediate(mem.displacement, 4)
                    
    def _apply_fixups(self):
        """Applies fixups for label references"""
        for offset, label in self.fixups:
            if label in self.external_symbols:
                continue  # Leave fixup for linker
            if label not in self.labels:
                raise ValueError(f"Undefined label: {label}")
                
            target = self.labels[label]
            rel = target - (offset + 4)  # Relative to next instruction
            
            # Update code
            self.code[offset:offset+4] = struct.pack('<i', rel)