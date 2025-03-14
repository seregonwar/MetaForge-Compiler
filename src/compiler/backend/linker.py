# MetaForge Compiler - Linker
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
# Module: Linker
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# This module is part of the MetaForge Compiler, a compiler for the
# MetaForge programming language. The module provides a linker for MetaForge,
# which is responsible for linking object files and libraries to generate
# executable files.
#
# Key Features:
# - Object file linking
# - Library linking
# - Generation of executable files
#
# Usage & Extensibility:
# The linker is used by the compiler to generate executable files from object
# files and libraries. It is not intended to be used directly by users.
#
# ---------------------------------------------------------------------------------
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
import struct
from .pe_generator import PEGenerator, Section

@dataclass
class Symbol:
    name: str
    address: int
    size: int
    is_external: bool = False
    is_exported: bool = False

@dataclass 
class Relocation:
    offset: int
    type: int
    symbol: str
    addend: int = 0

class Linker:
    def __init__(self):
        self.symbols: Dict[str, Symbol] = {}
        self.relocations: List[Relocation] = []
        self.sections: Dict[str, bytes] = {}
        self.imports: Dict[str, List[str]] = {}  # DLL -> [symbols]
        self.exports: List[str] = []
        
    def add_object(self, obj_file: bytes):
        """Adds an object file to the linking process"""
        # Parse object file
        symbols, relocations, sections = self._parse_object(obj_file)
        
        # Merge symbols
        for name, symbol in symbols.items():
            if name in self.symbols and not symbol.is_external:
                if not self.symbols[name].is_external:
                    raise Exception(f"Symbol {name} defined multiple times")
            else:
                self.symbols[name] = symbol
                
        # Add relocations
        self.relocations.extend(relocations)
        
        # Merge sections
        for name, data in sections.items():
            if name not in self.sections:
                self.sections[name] = data
            else:
                self.sections[name] += data
                
    def add_library(self, lib_file: Path):
        """Adds a library to the linking process"""
        # Parse library exports
        exports = self._parse_library(lib_file)
        
        # Add as external symbols
        for name in exports:
            if name not in self.symbols:
                self.symbols[name] = Symbol(
                    name=name,
                    address=0,
                    size=0,
                    is_external=True
                )
                
    def link(self) -> bytes:
        """Performs linking and generates executable file"""
        # Allocate addresses for symbols
        self._allocate_addresses()
        
        # Apply relocations
        self._apply_relocations()
        
        # Generate PE file
        return self._generate_pe()
        
    def _allocate_addresses(self):
        """Allocates virtual addresses for all symbols"""
        current_rva = 0x1000  # Base RVA
        
        # First the sections
        for name, data in self.sections.items():
            # Align to 4KB
            current_rva = (current_rva + 0xFFF) & ~0xFFF
            
            # Update symbols in section
            for symbol in self.symbols.values():
                if not symbol.is_external and symbol.address >= 0:
                    symbol.address += current_rva
                    
            current_rva += len(data)
            
    def _apply_relocations(self):
        """Applies relocations"""
        for reloc in self.relocations:
            symbol = self.symbols[reloc.symbol]
            if symbol.is_external:
                # Create import stub
                dll_name = self._find_export_dll(reloc.symbol)
                if dll_name:
                    if dll_name not in self.imports:
                        self.imports[dll_name] = []
                    if reloc.symbol not in self.imports[dll_name]:
                        self.imports[dll_name].append(reloc.symbol)
            else:
                # Apply relocation
                target_addr = symbol.address + reloc.addend
                self._write_relocation(reloc.offset, reloc.type, target_addr)
                
    def _write_relocation(self, offset: int, type: int, target: int):
        """Writes a relocation to the appropriate section"""
        if type == 0:  # REL32
            value = target - (offset + 4)  # Relative to next instruction
            struct.pack_into('<i', self.sections['.text'], offset, value)
        elif type == 1:  # DIR64
            struct.pack_into('<Q', self.sections['.text'], offset, target)
            
    def _find_export_dll(self, symbol: str) -> Optional[str]:
        """Finds the DLL that exports a symbol"""
        # Common Windows DLLs and their exports
        dll_exports = {
            'kernel32.dll': ['ExitProcess', 'GetStdHandle', 'WriteFile'],
            'msvcrt.dll': ['printf', 'scanf', 'malloc', 'free'],
            'user32.dll': ['MessageBoxA', 'MessageBoxW']
        }
        
        # Search for symbol in DLL exports
        for dll, exports in dll_exports.items():
            if symbol in exports:
                return dll
                
        return None
        
    def _generate_pe(self) -> bytes:
        """Generates the final PE file"""
        pe = PEGenerator()
        
        # Add sections
        for name, data in self.sections.items():
            characteristics = 0
            if name == '.text':
                characteristics = 0x60000020  # CODE|EXECUTE|READ
            elif name == '.data':
                characteristics = 0xC0000040  # INITIALIZED_DATA|READ|WRITE
                
            pe.add_section(Section(
                name=name,
                virtual_address=self.symbols[name].address,
                virtual_size=len(data),
                raw_data_size=len(data),
                raw_data_ptr=0,  # Will be calculated by PE generator
                characteristics=characteristics,
                data=data
            ))
            
        # Add imports
        for dll, functions in self.imports.items():
            for func in functions:
                pe.add_import(dll, func)
                
        # Set entry point
        if '_start' in self.symbols:
            pe.entry_point = self.symbols['_start'].address
            
        # Generate PE file
        return pe.generate()
        
    def _parse_object(self, data: bytes) -> Tuple[Dict[str, Symbol], List[Relocation], Dict[str, bytes]]:
        """Parses a COFF object file"""
        symbols = {}
        relocations = []
        sections = {}
        
        # Parse COFF header
        (machine, num_sections, timestamp, symtab_offset, num_symbols, 
         opt_header_size, characteristics) = struct.unpack('<HHIIIHH', data[:20])
         
        # Parse sections
        offset = 20 + opt_header_size
        for i in range(num_sections):
            section_header = data[offset:offset+40]
            name = section_header[:8].rstrip(b'\0').decode('ascii')
            size = struct.unpack('<I', section_header[16:20])[0]
            data_offset = struct.unpack('<I', section_header[20:24])[0]
            
            # Read section data
            sections[name] = data[data_offset:data_offset+size]
            
            # Add section symbol
            symbols[name] = Symbol(name, i, 0, False)
            
            offset += 40
            
        # Parse symbol table
        string_table_offset = symtab_offset + num_symbols * 18
        for i in range(num_symbols):
            sym_offset = symtab_offset + i * 18
            sym_data = data[sym_offset:sym_offset+18]
            
            # Get symbol name
            name_offset = struct.unpack('<I', sym_data[0:4])[0]
            if name_offset == 0:
                name = sym_data[0:8].rstrip(b'\0').decode('ascii')
            else:
                name_end = data.find(b'\0', string_table_offset + name_offset)
                name = data[string_table_offset + name_offset:name_end].decode('ascii')
                
            value = struct.unpack('<I', sym_data[8:12])[0]
            section_num = struct.unpack('<H', sym_data[12:14])[0]
            
            # Add symbol
            symbols[name] = Symbol(name, section_num, value, section_num == 0)
            
        return symbols, relocations, sections
        
    def _parse_library(self, lib_file: Path) -> List[str]:
        """Parses a library and returns exported symbols"""
        exports = []
        
        with open(lib_file, 'rb') as f:
            # Read library header
            if f.read(8) != b'!<arch>\n':
                raise ValueError("Invalid library format")
                
            # Read first linker member
            size = int(f.read(60)[48:58])
            symbols = struct.unpack('<I', f.read(4))[0]
            
            # Read symbol offsets
            offsets = []
            for i in range(symbols):
                offsets.append(struct.unpack('<I', f.read(4))[0])
                
            # Read symbol names
            for i in range(symbols):
                name_end = f.read().find(b'\0')
                exports.append(f.read(name_end).decode('ascii'))
                f.seek(1, 1)  # Skip null terminator
                
        return exports