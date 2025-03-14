# MetaForge Compiler - COFF Parser
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
# Module: COFF Parser
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# The COFF parser module is part of the MetaForge compiler and is used to parse
# COFF (Common Object File Format) files. The parser is responsible for reading
# the file and extracting the necessary information.
#
# Key Features:
# - Parse COFF files
# - Extract information from the file
#
# Usage & Extensibility:
# The COFF parser module is used by the MetaForge compiler to parse COFF files.
# It can be used by other modules to parse COFF files and extract the necessary
# information.
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, BinaryIO, Tuple
import struct

# COFF File Header Constants
IMAGE_FILE_MACHINE_AMD64 = 0x8664
IMAGE_FILE_MACHINE_I386 = 0x14c

class SectionFlags(Enum):
    TEXT = 0x20  # Code
    DATA = 0x40  # Initialized data
    BSS = 0x80   # Uninitialized data
    INFO = 0x200 # Comments/info

@dataclass
class CoffHeader:
    machine: int
    num_sections: int
    timestamp: int
    symtab_offset: int
    num_symbols: int
    opt_header_size: int
    characteristics: int

@dataclass 
class SectionHeader:
    name: str
    virtual_size: int
    virtual_address: int
    raw_data_size: int
    raw_data_ptr: int
    reloc_ptr: int
    linenum_ptr: int
    num_relocs: int
    num_linenum: int
    characteristics: int

@dataclass
class Symbol:
    name: str
    value: int
    section_number: int
    type: int
    storage_class: int
    aux_symbols: int

@dataclass
class Relocation:
    virtual_address: int
    symbol_index: int
    type: int

class CoffParser:
    def __init__(self, file: BinaryIO):
        self.file = file
        self.string_table: Dict[int, str] = {}
        self.symbols: List[Symbol] = []
        self.sections: List[Tuple[SectionHeader, bytes, List[Relocation]]] = []
        
    def parse(self) -> Tuple[List[Symbol], List[Tuple[SectionHeader, bytes, List[Relocation]]]]:
        """Parse the COFF file"""
        # Parse header
        header = self._parse_header()
        
        # Parse section headers
        section_headers = []
        for _ in range(header.num_sections):
            section_headers.append(self._parse_section_header())
            
        # Parse string table
        if header.symtab_offset > 0:
            self._parse_string_table(header.symtab_offset)
            
        # Parse symbols
        if header.num_symbols > 0:
            self.file.seek(header.symtab_offset)
            for _ in range(header.num_symbols):
                self.symbols.append(self._parse_symbol())
                
        # Parse sections
        for hdr in section_headers:
            data = self._parse_section_data(hdr)
            relocs = self._parse_relocations(hdr)
            self.sections.append((hdr, data, relocs))
            
        return self.symbols, self.sections
        
    def _parse_header(self) -> CoffHeader:
        """Parse COFF header"""
        data = self.file.read(20)
        machine, num_sections, timestamp, symtab_offset, num_symbols, opt_header_size, characteristics = struct.unpack("<HHIIIHH", data)
        
        return CoffHeader(
            machine=machine,
            num_sections=num_sections,
            timestamp=timestamp,
            symtab_offset=symtab_offset,
            num_symbols=num_symbols,
            opt_header_size=opt_header_size,
            characteristics=characteristics
        )
        
    def _parse_section_header(self) -> SectionHeader:
        """Parse section header"""
        data = self.file.read(40)
        name = data[:8].rstrip(b'\0').decode('ascii')
        virtual_size, virtual_address, raw_data_size, raw_data_ptr, reloc_ptr, linenum_ptr, num_relocs, num_linenum, characteristics = struct.unpack("<IIIIIIHHI", data[8:])
        
        # Handle long names in string table
        if name.startswith('/'):
            name = self.string_table[int(name[1:])]
            
        return SectionHeader(
            name=name,
            virtual_size=virtual_size,
            virtual_address=virtual_address,
            raw_data_size=raw_data_size,
            raw_data_ptr=raw_data_ptr,
            reloc_ptr=reloc_ptr,
            linenum_ptr=linenum_ptr,
            num_relocs=num_relocs,
            num_linenum=num_linenum,
            characteristics=characteristics
        )
        
    def _parse_string_table(self, offset: int):
        """Parse string table"""
        self.file.seek(offset)
        size = struct.unpack("<I", self.file.read(4))[0]
        
        # Read all strings
        pos = 4
        while pos < size:
            start = pos
            string = b''
            while True:
                c = self.file.read(1)
                if c == b'\0':
                    break
                string += c
                pos += 1
            self.string_table[start] = string.decode('ascii')
            pos += 1
            
    def _parse_symbol(self) -> Symbol:
        """Parse symbol table entry"""
        data = self.file.read(18)
        
        # Parse name/offset
        name_offset = struct.unpack("<I", data[:4])[0]
        if name_offset == 0:
            name = data[4:8].rstrip(b'\0').decode('ascii')
        else:
            name = self.string_table[name_offset]
            
        value, section_number, type_, storage_class, aux_symbols = struct.unpack("<IHBBB", data[8:])
        
        # Skip auxiliary symbol records
        self.file.seek(18 * aux_symbols, 1)
        
        return Symbol(
            name=name,
            value=value,
            section_number=section_number,
            type=type_,
            storage_class=storage_class,
            aux_symbols=aux_symbols
        )
        
    def _parse_section_data(self, header: SectionHeader) -> bytes:
        """Parse section data"""
        if header.raw_data_size > 0:
            self.file.seek(header.raw_data_ptr)
            return self.file.read(header.raw_data_size)
        return b''
        
    def _parse_relocations(self, header: SectionHeader) -> List[Relocation]:
        """Parse relocations for a section"""
        relocations = []
        
        if header.num_relocs > 0:
            self.file.seek(header.reloc_ptr)
            for _ in range(header.num_relocs):
                data = self.file.read(10)
                virtual_address, symbol_index, type_ = struct.unpack("<IIH", data)
                relocations.append(Relocation(
                    virtual_address=virtual_address,
                    symbol_index=symbol_index,
                    type=type_
                ))
                
        return relocations 