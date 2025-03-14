# MetaForge Compiler - Library Parser
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
# Module: Library Parser
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# The module provides a parser for library files, which are used by the
# MetaForge compiler to generate object files.
#
# Key Features:
# - Parser for library files
# - Support for multiple object files
# - Support for debug information
#
# Usage & Extensibility:
# The module can be used to generate object files from library files.
# It can be extended to support additional features and functionality.
from dataclasses import dataclass
from typing import List, Dict, BinaryIO, Optional
from pathlib import Path
import struct
import time

@dataclass
class LibraryHeader:
    signature: str
    timestamp: int
    user_def_timestamp: int
    num_symbols: int
    first_linker_member: int
    first_longnames_member: int

@dataclass
class LibraryMember:
    name: str
    timestamp: int
    user_id: int
    group_id: int
    mode: int
    size: int
    offset: int
    data: Optional[bytes] = None

class LibraryParser:
    def __init__(self, file: BinaryIO):
        self.file = file
        self.header: Optional[LibraryHeader] = None
        self.members: List[LibraryMember] = []
        self.symbol_table: Dict[str, int] = {}  # symbol -> member offset
        self.longnames: Dict[int, str] = {}
        
    def parse(self) -> Dict[str, bytes]:
        """Parse library and return dictionary symbol -> object file"""
        # Parse header
        self.header = self._parse_header()
        
        # Parse symbol table
        self._parse_symbol_table()
        
        # Parse longnames if present
        if self.header.first_longnames_member > 0:
            self._parse_longnames()
            
        # Parse members
        self._parse_members()
        
        # Build result
        result = {}
        for symbol, member_offset in self.symbol_table.items():
            for member in self.members:
                if member.offset == member_offset:
                    result[symbol] = member.data
                    break
                    
        return result
        
    def _parse_header(self) -> LibraryHeader:
        """Parse library header"""
        data = self.file.read(60)
        signature = data[:8].decode('ascii')
        
        if signature != '!<arch>\n':
            raise ValueError("Invalid library signature")
            
        # Skip to first linker member
        self.file.seek(8)
        
        # Parse first linker member header
        member_header = self._parse_member_header()
        first_linker = self.file.tell() - 60
        
        # Parse second linker member header
        self.file.seek(first_linker + member_header.size + (member_header.size % 2))
        member_header = self._parse_member_header()
        first_longnames = self.file.tell() - 60
        
        # Parse number of symbols
        self.file.seek(first_linker + 60)
        num_symbols = struct.unpack("<I", self.file.read(4))[0]
        
        return LibraryHeader(
            signature=signature,
            timestamp=int(time.time()),
            user_def_timestamp=0,
            num_symbols=num_symbols,
            first_linker_member=first_linker,
            first_longnames_member=first_longnames
        )
        
    def _parse_member_header(self) -> LibraryMember:
        """Parse library member header"""
        data = self.file.read(60)
        
        name = data[:16].rstrip(b' ').decode('ascii')
        timestamp = int(data[16:28].rstrip(b' '))
        user_id = int(data[28:34].rstrip(b' '))
        group_id = int(data[34:40].rstrip(b' '))
        mode = int(data[40:48].rstrip(b' '), 8)
        size = int(data[48:58].rstrip(b' '))
        
        if data[58:60] != b'`\n':
            raise ValueError("Invalid member header end")
            
        return LibraryMember(
            name=name,
            timestamp=timestamp,
            user_id=user_id,
            group_id=group_id,
            mode=mode,
            size=size,
            offset=self.file.tell() - 60
        )
        
    def _parse_symbol_table(self):
        """Parse symbol table"""
        if self.header.first_linker_member <= 0:
            return
            
        self.file.seek(self.header.first_linker_member + 60)
        
        # Number of symbols
        num_symbols = struct.unpack("<I", self.file.read(4))[0]
        
        # Symbol offsets
        offsets = []
        for _ in range(num_symbols):
            offsets.append(struct.unpack("<I", self.file.read(4))[0])
            
        # Symbol names
        for i in range(num_symbols):
            name = b''
            while True:
                c = self.file.read(1)
                if c == b'\0':
                    break
                name += c
            self.symbol_table[name.decode('ascii')] = offsets[i]
            
    def _parse_longnames(self):
        """Parse long names table"""
        if self.header.first_longnames_member <= 0:
            return
            
        self.file.seek(self.header.first_longnames_member + 60)
        
        pos = 0
        while True:
            start = pos
            name = b''
            while True:
                c = self.file.read(1)
                if c == b'\0':
                    break
                name += c
                pos += 1
            if not name:
                break
            self.longnames[start] = name.decode('ascii')
            pos += 1
            
    def _parse_members(self):
        """Parse library members"""
        # Skip to first member after symbol table and longnames
        if self.header.first_longnames_member > 0:
            offset = self.header.first_longnames_member
        else:
            offset = self.header.first_linker_member
            
        self.file.seek(offset)
        
        while True:
            try:
                member = self._parse_member_header()
                
                # Handle long names
                if member.name.startswith('/'):
                    member.name = self.longnames[int(member.name[1:])]
                    
                # Read member data
                member.data = self.file.read(member.size)
                self.members.append(member)
                
                # Align to even boundary
                if member.size % 2:
                    self.file.seek(1, 1)
                    
            except Exception:
                break