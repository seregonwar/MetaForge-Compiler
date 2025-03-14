# MetaForge Compiler - x64 Assembler
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
# Module: x64 Assembler
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# This module is part of the MetaForge Compiler, a compiler for the
# MetaForge programming language.
# The module provides an x64 assembler for generating machine code
# from the intermediate representation (IR) generated by the compiler.
#
# Key Features:
# - Generates x64 machine code from the IR.
# - Supports basic arithmetic operations.
# - Supports basic memory operations.
#
# Usage & Extensibility:
# This module is used by the MetaForge compiler to generate x64
# machine code for the target platform.
# The module can be extended with new instructions and features.
#
# ---------------------------------------------------------------------------------
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
    value: Union[Register, int, str, Dict]

class X64Assembler:
    """Assembles x64 machine code directly"""
    
    def __init__(self):
        self.code = bytearray()
        self.labels = {}
        self.fixups = []
        self.rip = 0
        
    def assemble(self, instructions: List[Dict]) -> bytes:
        """Assembles a list of instructions into machine code"""
        self.code = bytearray()
        self.labels = {}
        self.fixups = []
        self.rip = 0
        
        # First pass - collect labels
        pos = 0
        for instr in instructions:
            if 'label' in instr:
                self.labels[instr['label']] = pos
            else:
                pos += self._get_instruction_size(instr)
                
        # Second pass - generate code
        for instr in instructions:
            if 'label' not in instr:
                self._emit_instruction(instr)
                
        # Apply fixups
        for offset, label in self.fixups:
            if label in self.labels:
                target = self.labels[label]
                rel = target - (offset + 4)  # Relative to next instruction
                self.code[offset:offset+4] = struct.pack('<i', rel)
                
        return bytes(self.code)
        
    def _emit_instruction(self, instr: Dict):
        """Emits a single instruction"""
        opcode = instr['opcode']
        operands = instr.get('operands', [])
        
        if opcode == 'push':
            self._emit_push(operands[0])
        elif opcode == 'pop':
            self._emit_pop(operands[0])
        elif opcode == 'mov':
            self._emit_mov(operands[0], operands[1])
        elif opcode == 'lea':
            self._emit_lea(operands[0], operands[1])
        elif opcode == 'call':
            if 'target' in instr:
                self._emit_call_label(instr['target'])
            else:
                self._emit_call_reg(operands[0])
        elif opcode == 'ret':
            self._emit_ret()
        elif opcode == 'sub':
            self._emit_sub(operands[0], operands[1])
        elif opcode == 'add':
            self._emit_add(operands[0], operands[1])
        elif opcode == 'xor':
            self._emit_xor(operands[0], operands[1])
            
    def _emit_push(self, op):
        """Emits PUSH instruction"""
        reg = self._get_register(op)
        if reg is not None:
            # REX prefix if needed
            if reg.value >= 8:
                self.code.append(0x41)
            # Opcode
            self.code.append(0x50 + (reg.value & 7))
            
    def _emit_pop(self, op):
        """Emits POP instruction"""
        reg = self._get_register(op)
        if reg is not None:
            # REX prefix if needed
            if reg.value >= 8:
                self.code.append(0x41)
            # Opcode
            self.code.append(0x58 + (reg.value & 7))
            
    def _emit_mov(self, dst, src):
        """Emits MOV instruction"""
        dst_reg = self._get_register(dst)
        src_reg = self._get_register(src)
        
        if dst_reg is not None:
            if isinstance(src, int):
                # mov reg, imm
                rex = 0x48 if dst_reg.value >= 8 else 0x40
                self.code.append(rex)
                self.code.append(0xB8 + (dst_reg.value & 7))
                # Handle negative numbers correctly
                if -0x80000000 <= src <= 0x7FFFFFFF:
                    self.code.extend(struct.pack('<i', src))
                else:
                    self.code.extend(struct.pack('<Q', src & 0xFFFFFFFFFFFFFFFF))
            elif src_reg is not None:
                # mov reg, reg
                rex = 0x48
                if dst_reg.value >= 8:
                    rex |= 0x44
                if src_reg.value >= 8:
                    rex |= 0x41
                self.code.append(rex)
                self.code.append(0x89)
                self.code.append(0xC0 + ((src_reg.value & 7) << 3) + (dst_reg.value & 7))
                
    def _emit_lea(self, dst, src):
        """Emits LEA instruction"""
        dst_reg = self._get_register(dst)
        if dst_reg is not None and isinstance(src, str):
            # lea reg, [label]
            rex = 0x48 if dst_reg.value >= 8 else 0x40
            self.code.append(rex)
            self.code.append(0x8D)
            self.code.append(0x05 + ((dst_reg.value & 7) << 3))
            # Add fixup for label
            self.fixups.append((len(self.code), src.strip('[]')))
            self.code.extend([0, 0, 0, 0])
            
    def _emit_call_label(self, label: str):
        """Emits CALL instruction with label"""
        self.code.append(0xE8)
        self.fixups.append((len(self.code), label))
        self.code.extend([0, 0, 0, 0])
        
    def _emit_call_reg(self, reg):
        """Emits CALL instruction with register"""
        reg_obj = self._get_register(reg)
        if reg_obj is not None:
            if reg_obj.value >= 8:
                self.code.append(0x41)
            self.code.append(0xFF)
            self.code.append(0xD0 + (reg_obj.value & 7))
            
    def _emit_ret(self):
        """Emits RET instruction"""
        self.code.append(0xC3)
        
    def _emit_sub(self, dst, src):
        """Emits SUB instruction"""
        dst_reg = self._get_register(dst)
        if dst_reg is not None and isinstance(src, int):
            # sub reg, imm
            rex = 0x48 if dst_reg.value >= 8 else 0x40
            self.code.append(rex)
            self.code.append(0x81)
            self.code.append(0xE8 + (dst_reg.value & 7))
            if -0x80 <= src <= 0x7F:
                self.code.extend(struct.pack('<b', src))
            else:
                self.code.extend(struct.pack('<i', src))
                
    def _emit_add(self, dst, src):
        """Emits ADD instruction"""
        dst_reg = self._get_register(dst)
        if dst_reg is not None and isinstance(src, int):
            # add reg, imm
            rex = 0x48 if dst_reg.value >= 8 else 0x40
            self.code.append(rex)
            self.code.append(0x81)
            self.code.append(0xC0 + (dst_reg.value & 7))
            if -0x80 <= src <= 0x7F:
                self.code.extend(struct.pack('<b', src))
            else:
                self.code.extend(struct.pack('<i', src))
                
    def _emit_xor(self, dst, src):
        """Emits XOR instruction"""
        dst_reg = self._get_register(dst)
        src_reg = self._get_register(src)
        if dst_reg is not None and src_reg is not None:
            # xor reg, reg
            rex = 0x48
            if dst_reg.value >= 8:
                rex |= 0x44
            if src_reg.value >= 8:
                rex |= 0x41
            self.code.append(rex)
            self.code.append(0x31)
            self.code.append(0xC0 + ((src_reg.value & 7) << 3) + (dst_reg.value & 7))
            
    def _get_register(self, op) -> Optional[Register]:
        """Gets Register enum from operand"""
        if isinstance(op, str):
            try:
                return Register[op.upper()]
            except KeyError:
                return None
        return None
        
    def _get_instruction_size(self, instr: Dict) -> int:
        """Gets the size of an instruction in bytes"""
        opcode = instr['opcode']
        operands = instr.get('operands', [])
        
        if opcode in ['push', 'pop']:
            return 1 + (1 if self._needs_rex(operands[0]) else 0)
        elif opcode == 'mov':
            return self._get_mov_size(operands[0], operands[1])
        elif opcode == 'lea':
            return 7  # REX + LEA + ModRM + displacement
        elif opcode == 'call':
            return 5 if 'target' in instr else 2
        elif opcode == 'ret':
            return 1
        elif opcode in ['add', 'sub']:
            return 4 + (1 if self._needs_rex(operands[0]) else 0)
        elif opcode == 'xor':
            return 3 + (1 if self._needs_rex(operands[0]) or self._needs_rex(operands[1]) else 0)
        return 0
        
    def _get_mov_size(self, dst, src) -> int:
        """Gets the size of a MOV instruction"""
        if isinstance(src, int):
            return 10  # REX + MOV + imm64
        return 3 + (1 if self._needs_rex(dst) or self._needs_rex(src) else 0)
        
    def _needs_rex(self, op) -> bool:
        """Checks if operand needs REX prefix"""
        reg = self._get_register(op)
        return reg is not None and reg.value >= 8