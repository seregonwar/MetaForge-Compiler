# MetaForge Compiler - PE File Generator
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
# Module: PE File Generator
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# The PE File Generator is a module which takes a list of sections and generates
# a Windows PE file from them.
#
# Key Features:
# - Generates a Windows PE file
# - Supports generation of x86, x64 and ARM PE files
# - Supports generation of PE files with and without relocation sections
#
# Usage & Extensibility:
# This module can be used to generate a PE file from a list of sections. The
# sections can be created using the Section class in this module. The PE file
# can then be written to a file using the dump method of the PELoader class.
#
# ---------------------------------------------------------------------------------
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, BinaryIO
import struct
from pathlib import Path
import os
import logging
import stat
import time
import tempfile
import shutil
import uuid
import sys
import ctypes

# PE File Format Constants
IMAGE_DOS_SIGNATURE = 0x5A4D
IMAGE_NT_SIGNATURE = 0x00004550
IMAGE_FILE_MACHINE_AMD64 = 0x8664
IMAGE_FILE_EXECUTABLE_IMAGE = 0x0002
IMAGE_FILE_LARGE_ADDRESS_AWARE = 0x0020
IMAGE_SUBSYSTEM_WINDOWS_CUI = 0x0003
IMAGE_NUMBEROF_DIRECTORY_ENTRIES = 16
IMAGE_SECTION_ALIGNMENT = 0x1000
IMAGE_FILE_ALIGNMENT = 0x200

@dataclass
class Section:
    name: str
    virtual_address: int
    virtual_size: int
    raw_data_size: int
    raw_data_ptr: int
    characteristics: int
    data: bytes

class PEGenerator:
    def __init__(self):
        self.sections: List[Section] = []
        self.imports: Dict[str, List[str]] = {}  # DLL -> [function names]
        self.exports: List[str] = []
        self.relocations: List[tuple] = []  # [(rva, type), ...]
        self.entry_point: int = 0
        self.machine: int = IMAGE_FILE_MACHINE_AMD64
        self.characteristics: int = IMAGE_FILE_EXECUTABLE_IMAGE | IMAGE_FILE_LARGE_ADDRESS_AWARE
        self.subsystem: int = IMAGE_SUBSYSTEM_WINDOWS_CUI
        self.image_base: int = 0x400000
        
    def generate(self, output_file: Path) -> bool:
        try:
            # Add import section if needed
            if self.imports:
                self._add_import_section()
                
            # Add export section if needed
            if self.exports:
                self._add_export_section()
                
            # Add relocation section if needed
            if self.relocations:
                self._add_relocation_section()
                
            # Calculate file layout
            file_offset = self._calculate_headers_size()
            image_size = file_offset
            
            for section in self.sections:
                # Align section's virtual address
                section.virtual_address = self._align_up(image_size, IMAGE_SECTION_ALIGNMENT)
                image_size = section.virtual_address + self._align_up(section.virtual_size, IMAGE_SECTION_ALIGNMENT)
                
                # Align raw data
                section.raw_data_ptr = self._align_up(file_offset, IMAGE_FILE_ALIGNMENT)
                file_offset = section.raw_data_ptr + self._align_up(section.raw_data_size, IMAGE_FILE_ALIGNMENT)
                
            # Generate PE file
            with open(output_file, 'wb') as f:
                # DOS Header
                f.write(self._generate_dos_header())
                
                # NT Headers
                f.write(self._generate_nt_headers(image_size))
                
                # Section Headers
                f.write(self._generate_section_headers())
                
                # Section Data
                for section in self.sections:
                    # Pad to section alignment
                    while f.tell() < section.raw_data_ptr:
                        f.write(b'\0')
                        
                    # Write section data
                    f.write(section.data)
                    
                    # Pad to file alignment
                    aligned_size = self._align_up(section.raw_data_size, IMAGE_FILE_ALIGNMENT)
                    while f.tell() < section.raw_data_ptr + aligned_size:
                        f.write(b'\0')
                        
            return True
            
        except Exception as e:
            logging.error(f"Error generating PE file: {str(e)}", exc_info=True)
            return False
            
    def _generate_dos_header(self) -> bytes:
        """Generates DOS header and stub"""
        # Basic DOS header
        dos_header = bytearray(64)
        
        # MZ signature
        struct.pack_into('<H', dos_header, 0, IMAGE_DOS_SIGNATURE)
        
        # Offset to PE header
        struct.pack_into('<I', dos_header, 0x3C, 64)
        
        # DOS stub (simple ret)
        dos_stub = b'\x0E\x1F\xBA\x0E\x00\xB4\x09\xCD\x21\xB8\x01\x4C\xCD\x21'
        dos_header[64-len(dos_stub):64] = dos_stub
        
        return bytes(dos_header)
        
    def _generate_nt_headers(self, image_size: int) -> bytes:
        """Generates NT headers"""
        # PE Signature
        nt_headers = struct.pack('<I', IMAGE_NT_SIGNATURE)
        
        # File Header
        nt_headers += struct.pack('<HHIIIHH',
            self.machine,                    # Machine
            len(self.sections),              # NumberOfSections
            int(time.time()),                # TimeDateStamp
            0,                               # PointerToSymbolTable
            0,                               # NumberOfSymbols
            224,                             # SizeOfOptionalHeader
            self.characteristics             # Characteristics
        )
        
        # Optional Header
        nt_headers += struct.pack('<HBBIIIIIIIIIHHHHHHIIIIII',
            0x20B,                          # Magic (PE32+)
            1,                              # MajorLinkerVersion
            0,                              # MinorLinkerVersion
            0,                              # SizeOfCode
            0,                              # SizeOfInitializedData
            0,                              # SizeOfUninitializedData
            self.entry_point,               # AddressOfEntryPoint
            0x1000,                         # BaseOfCode
            self.image_base,                # ImageBase
            IMAGE_SECTION_ALIGNMENT,        # SectionAlignment
            IMAGE_FILE_ALIGNMENT,           # FileAlignment
            6,                              # MajorOperatingSystemVersion
            0,                              # MinorOperatingSystemVersion
            0,                              # MajorImageVersion
            0,                              # MinorImageVersion
            6,                              # MajorSubsystemVersion
            0,                              # MinorSubsystemVersion
            0,                              # Win32VersionValue
            image_size,                     # SizeOfImage
            self._calculate_headers_size(),  # SizeOfHeaders
            0,                              # CheckSum
            self.subsystem,                 # Subsystem
            0x8160,                         # DllCharacteristics
            0x100000,                       # SizeOfStackReserve
            0x1000,                         # SizeOfStackCommit
            0x100000,                       # SizeOfHeapReserve
            0x1000                          # SizeOfHeapCommit
        )
        
        # Data Directories
        for i in range(IMAGE_NUMBEROF_DIRECTORY_ENTRIES):
            nt_headers += struct.pack('<II', 0, 0)
            
        return nt_headers
        
    def _generate_section_headers(self) -> bytes:
        """Generates section headers"""
        headers = bytearray()
        
        for section in self.sections:
            # Convert name to bytes (padded with nulls)
            name_bytes = section.name.encode('ascii')[:8]
            name_bytes = name_bytes.ljust(8, b'\0')
            
            headers += name_bytes
            
            headers += struct.pack('<IIIIIIII',
                section.virtual_size,        # VirtualSize
                section.virtual_address,     # VirtualAddress
                section.raw_data_size,       # SizeOfRawData
                section.raw_data_ptr,        # PointerToRawData
                0,                           # PointerToRelocations
                0,                           # PointerToLinenumbers
                0,                           # NumberOfRelocations
                section.characteristics      # Characteristics
            )
            
        return bytes(headers)
        
    def _calculate_headers_size(self) -> int:
        """Calculates total size of headers"""
        return self._align_up(
            64 +                            # DOS Header
            4 +                             # PE Signature
            20 +                            # File Header
            224 +                           # Optional Header
            len(self.sections) * 40,        # Section Headers
            IMAGE_FILE_ALIGNMENT
        )
        
    def _align_up(self, value: int, alignment: int) -> int:
        """Aligns value up to the nearest multiple of alignment"""
        return (value + alignment - 1) & ~(alignment - 1)
        
    def add_section(self, section: Section):
        self.sections.append(section)
        
    def add_import(self, dll: str, functions: List[str]):
        if dll not in self.imports:
            self.imports[dll] = []
        self.imports[dll].extend(functions)
        
    def add_export(self, function: str):
        self.exports.append(function)
        
    def add_relocation(self, rva: int, type: int):
        self.relocations.append((rva, type))
        
    def _add_import_section(self):
        """Adds the import section"""
        # Calculate required size
        size = 0
        
        # Import Directory Table
        size += (len(self.imports) + 1) * 20  # +1 for NULL terminator
        
        # Import Lookup Tables
        for functions in self.imports.values():
            size += (len(functions) + 1) * 8  # +1 for NULL terminator
            
        # Hint/Name Table
        name_table_size = 0
        for dll, functions in self.imports.items():
            name_table_size += len(dll) + 1  # DLL name + NULL
            for func in functions:
                name_table_size += 2 + len(func) + 1  # Hint + name + NULL
                
        size += name_table_size
        
        # Create section
        import_data = bytearray(size)
        current_offset = 0
        
        # Import Directory Table
        idt_offset = current_offset
        current_offset += (len(self.imports) + 1) * 20
        
        # Import Lookup Tables
        ilt_offsets = {}
        for dll in self.imports:
            ilt_offsets[dll] = current_offset
            current_offset += (len(self.imports[dll]) + 1) * 8
            
        # Hint/Name Table
        hint_name_offset = current_offset
        current_offset = hint_name_offset
        
        # Write Hint/Name Table
        name_rvas = {}
        for dll, functions in self.imports.items():
            name_rvas[dll] = {}
            for func in functions:
                name_rvas[dll][func] = current_offset - hint_name_offset
                
                # Hint (0 for now)
                import_data[current_offset:current_offset+2] = struct.pack('<H', 0)
                current_offset += 2
                
                # Function name
                import_data[current_offset:current_offset+len(func)] = func.encode('ascii')
                current_offset += len(func)
                import_data[current_offset] = 0  # NULL terminator
                current_offset += 1
                
        # Write Import Lookup Tables
        for dll, functions in self.imports.items():
            offset = ilt_offsets[dll]
            for func in functions:
                # Ordinal bit clear, RVA to Hint/Name
                import_data[offset:offset+8] = struct.pack('<Q', name_rvas[dll][func])
                offset += 8
            # NULL terminator
            import_data[offset:offset+8] = b'\0' * 8
            
        # Write Import Directory Table
        offset = idt_offset
        for dll, functions in self.imports.items():
            # Import Directory Entry
            struct.pack_into('<IIIII', import_data, offset,
                ilt_offsets[dll],  # OriginalFirstThunk
                0,                 # TimeDateStamp
                0,                 # ForwarderChain
                hint_name_offset,  # Name
                ilt_offsets[dll]   # FirstThunk
            )
            offset += 20
            
        # NULL terminator
        import_data[offset:offset+20] = b'\0' * 20
        
        # Add section
        self.sections.append(Section(
            name=".idata",
            virtual_address=0x3000,  # After .text and .data
            virtual_size=len(import_data),
            raw_data_size=len(import_data),
            raw_data_ptr=0,  # Will be calculated later
            characteristics=0xC0000040,  # INITIALIZED_DATA|READ|WRITE
            data=bytes(import_data)
        ))
        
    def _add_export_section(self):
        """Adds the export section"""
        if not self.exports:
            return
            
        # Calculate required size
        names_size = sum(len(name) + 1 for name in self.exports.keys())
        export_data = bytearray(40 + len(self.exports) * 4 + names_size)
        
        # Export Directory Table
        struct.pack_into('<IIIIIIII', export_data, 0,
            0,                  # Characteristics
            0,                  # TimeDateStamp 
            0,                  # MajorVersion/MinorVersion
            0,                  # Name RVA
            1,                  # OrdinalBase
            len(self.exports),  # NumberOfFunctions
            len(self.exports),  # NumberOfNames
            40                  # AddressOfFunctions
        )
        
        # Function addresses
        addr_offset = 40
        for addr in self.exports.values():
            struct.pack_into('<I', export_data, addr_offset, addr)
            addr_offset += 4
            
        # Function names
        name_offset = addr_offset + len(self.exports) * 4
        for name in self.exports.keys():
            name_bytes = name.encode('ascii') + b'\0'
            export_data[name_offset:name_offset+len(name_bytes)] = name_bytes
            name_offset += len(name_bytes)
            
        # Add section
        self.sections.append(Section(
            name=".edata",
            virtual_address=0x4000,  # After .idata
            virtual_size=len(export_data),
            raw_data_size=len(export_data),
            raw_data_ptr=0,
            characteristics=0x40000040,  # INITIALIZED_DATA|READ
            data=bytes(export_data)
        ))
        
    def _add_relocation_section(self):
        """Adds the relocation section"""
        if not self.relocations:
            return
            
        # Group relocations by page
        pages = {}
        for rva in self.relocations:
            page_rva = rva & ~0xFFF  # Page aligned address
            if page_rva not in pages:
                pages[page_rva] = []
            pages[page_rva].append(rva & 0xFFF)  # Offset within page
            
        # Calculate size and create buffer
        total_size = sum(8 + len(entries) * 2 for entries in pages.values())
        reloc_data = bytearray(total_size)
        
        # Write relocation blocks
        offset = 0
        for page_rva, entries in pages.items():
            # Block header
            struct.pack_into('<II', reloc_data, offset,
                page_rva,                    # Page RVA
                8 + len(entries) * 2         # Block Size
            )
            offset += 8
            
            # Relocation entries (type 3 = HIGH_LOW)
            for entry in entries:
                struct.pack_into('<H', reloc_data, offset, 0x3000 | entry)
                offset += 2
                
        # Add section
        self.sections.append(Section(
            name=".reloc",
            virtual_address=0x5000,  # After .edata
            virtual_size=len(reloc_data),
            raw_data_size=len(reloc_data),
            raw_data_ptr=0,
            characteristics=0x42000040,  # INITIALIZED_DATA|DISCARDABLE|READ
            data=bytes(reloc_data)
        ))
        
    def generate(self, output_file: Path, code: bytes, data: bytes):
        """Generates the PE file"""
        try:
            # Check if we have required permissions
            if os.name == 'nt':  # Windows
                if not ctypes.windll.shell32.IsUserAnAdmin():
                    logging.warning("Insufficient permissions. Requesting elevation...")
                    # Restart process with admin privileges
                    if not ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join(sys.argv), None, 1
                    ):
                        raise PermissionError("Failed to elevate privileges. Please run as administrator.")
                    sys.exit(0)  # Terminate original process

            # Create output directory if it doesn't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create sections
            text_section = Section(
                name=".text",
                virtual_address=0x1000,
                virtual_size=len(code),
                raw_data_size=len(code),
                raw_data_ptr=0,
                characteristics=0x60000020,  # CODE|EXECUTE|READ
                data=code
            )
            
            data_section = Section(
                name=".data",
                virtual_address=0x2000,
                virtual_size=len(data),
                raw_data_size=len(data),
                raw_data_ptr=0,
                characteristics=0xC0000040,  # INITIALIZED_DATA|READ|WRITE
                data=data
            )
            
            self.sections = [text_section, data_section]
            
            # Add import section if needed
            if self.imports:
                self._add_import_section()
                
            # Calculate offsets
            current_offset = self._calculate_headers_size()
            for section in self.sections:
                # Align to 512 bytes
                current_offset = (current_offset + 511) & ~511
                section.raw_data_ptr = current_offset
                current_offset += section.raw_data_size
                
            # Write PE file
            with open(output_file, 'wb') as f:
                # Write DOS header
                self._write_dos_header(f)
                
                # Write NT headers
                self.entry_point = 0x1000  # Entry point at start of code
                self._write_nt_headers(f)
                
                # Write section headers
                self._write_section_headers(f)
                
                # Write sections
                for section in self.sections:
                    # Go to section offset
                    current_pos = f.tell()
                    padding = section.raw_data_ptr - current_pos
                    if padding > 0:
                        f.write(bytes(padding))
                        
                    # Write section data
                    f.write(section.data)
                    
                    # Padding at end of section
                    end_padding = ((section.raw_data_size + 511) & ~511) - section.raw_data_size
                    if end_padding > 0:
                        f.write(bytes(end_padding))
                        
                # Ensure everything is written
                f.flush()
                os.fsync(f.fileno())
                
            # Verify file was created correctly
            if not output_file.exists():
                raise RuntimeError("Failed to create output file")
                
            file_size = output_file.stat().st_size
            if file_size == 0:
                raise RuntimeError("Generated file is empty")
                
            logging.info(f"Successfully generated PE file: {output_file} ({file_size} bytes)")
            
        except Exception as e:
            logging.error(f"Failed to generate PE file: {e}")
            # Clean up partial file on error
            try:
                if output_file.exists():
                    output_file.unlink()
            except:
                pass
            raise
        
    def _calculate_headers_size(self) -> int:
        """Calculates total size of headers"""
        size = 0
        size += 0x40  # DOS header
        size += 0x4   # PE signature
        size += 0x14  # File header
        size += 0xF0  # Optional header
        size += len(self.sections) * 0x28  # Section headers
        return (size + 511) & ~511  # Align to 512 bytes
        
    def _write_dos_header(self, f: BinaryIO):
        """Writes the DOS header"""
        # DOS Header magic (MZ)
        f.write(struct.pack('<H', IMAGE_DOS_SIGNATURE))
        
        # DOS Header stub program
        dos_stub = bytes([
            0x0E, 0x1F, 0xBA, 0x0E, 0x00, 0xB4, 0x09, 0xCD,
            0x21, 0xB8, 0x01, 0x4C, 0xCD, 0x21, 0x54, 0x68,
            0x69, 0x73, 0x20, 0x70, 0x72, 0x6F, 0x67, 0x72,
            0x61, 0x6D, 0x20, 0x63, 0x61, 0x6E, 0x6E, 0x6F,
            0x74, 0x20, 0x62, 0x65, 0x20, 0x72, 0x75, 0x6E,
            0x20, 0x69, 0x6E, 0x20, 0x44, 0x4F, 0x53, 0x20,
            0x6D, 0x6F, 0x64, 0x65, 0x2E, 0x0D, 0x0D, 0x0A,
            0x24, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        f.write(dos_stub)
        
        # PE Header offset
        f.write(struct.pack('<I', 0x80))  # e_lfanew
        
    def _write_nt_headers(self, f: BinaryIO):
        """Writes the NT headers"""
        # PE Signature
        f.write(struct.pack('<I', IMAGE_NT_SIGNATURE))
        
        # File Header
        f.write(struct.pack('<H', IMAGE_FILE_MACHINE_AMD64))  # Machine
        f.write(struct.pack('<H', len(self.sections)))        # NumberOfSections
        f.write(struct.pack('<I', 0))                         # TimeDateStamp
        f.write(struct.pack('<I', 0))                         # PointerToSymbolTable
        f.write(struct.pack('<I', 0))                         # NumberOfSymbols
        f.write(struct.pack('<H', 0xF0))                      # SizeOfOptionalHeader
        f.write(struct.pack('<H', IMAGE_FILE_EXECUTABLE_IMAGE | IMAGE_FILE_LARGE_ADDRESS_AWARE))  # Characteristics
        
        # Optional Header
        f.write(struct.pack('<H', 0x20B))  # Magic (PE32+)
        f.write(struct.pack('<B', 1))      # MajorLinkerVersion
        f.write(struct.pack('<B', 0))      # MinorLinkerVersion
        f.write(struct.pack('<I', sum(s.raw_data_size for s in self.sections if s.characteristics & 0x20)))  # SizeOfCode
        f.write(struct.pack('<I', sum(s.raw_data_size for s in self.sections if s.characteristics & 0x40)))  # SizeOfInitializedData
        f.write(struct.pack('<I', 0))      # SizeOfUninitializedData
        f.write(struct.pack('<I', self.entry_point))  # AddressOfEntryPoint
        f.write(struct.pack('<I', 0x1000)) # BaseOfCode
        
        # PE32+ specific
        f.write(struct.pack('<Q', 0x140000000))  # ImageBase
        f.write(struct.pack('<I', 0x1000))       # SectionAlignment
        f.write(struct.pack('<I', 0x200))        # FileAlignment
        f.write(struct.pack('<H', 6))            # MajorOperatingSystemVersion
        f.write(struct.pack('<H', 0))            # MinorOperatingSystemVersion
        f.write(struct.pack('<H', 0))            # MajorImageVersion
        f.write(struct.pack('<H', 0))            # MinorImageVersion
        f.write(struct.pack('<H', 6))            # MajorSubsystemVersion
        f.write(struct.pack('<H', 0))            # MinorSubsystemVersion
        f.write(struct.pack('<I', 0))            # Win32VersionValue
        f.write(struct.pack('<I', self._calculate_image_size()))  # SizeOfImage
        f.write(struct.pack('<I', self._calculate_headers_size()))# SizeOfHeaders
        f.write(struct.pack('<I', 0))            # CheckSum
        f.write(struct.pack('<H', IMAGE_SUBSYSTEM_WINDOWS_CUI))  # Subsystem
        f.write(struct.pack('<H', 0x8160))       # DllCharacteristics
        f.write(struct.pack('<Q', 0x100000))     # SizeOfStackReserve
        f.write(struct.pack('<Q', 0x1000))       # SizeOfStackCommit
        f.write(struct.pack('<Q', 0x100000))     # SizeOfHeapReserve
        f.write(struct.pack('<Q', 0x1000))       # SizeOfHeapCommit
        f.write(struct.pack('<I', 0))            # LoaderFlags
        f.write(struct.pack('<I', 16))           # NumberOfRvaAndSizes
        
        # Data Directories
        for i in range(16):
            if i == 1 and self.imports:  # Import Directory
                f.write(struct.pack('<I', 0x3000))  # RVA
                f.write(struct.pack('<I', 0x100))   # Size
            else:
                f.write(struct.pack('<Q', 0))       # Empty directory
                
    def _write_section_headers(self, f: BinaryIO):
        """Writes the section headers"""
        for section in self.sections:
            name = section.name.encode('ascii')[:8].ljust(8, b'\0')
            f.write(name)  # Name
            f.write(struct.pack('<I', section.virtual_size))      # VirtualSize
            f.write(struct.pack('<I', section.virtual_address))   # VirtualAddress
            f.write(struct.pack('<I', section.raw_data_size))    # SizeOfRawData
            f.write(struct.pack('<I', section.raw_data_ptr))     # PointerToRawData
            f.write(struct.pack('<I', 0))                        # PointerToRelocations
            f.write(struct.pack('<I', 0))                        # PointerToLinenumbers
            f.write(struct.pack('<H', 0))                        # NumberOfRelocations
            f.write(struct.pack('<H', 0))                        # NumberOfLinenumbers
            f.write(struct.pack('<I', section.characteristics))  # Characteristics
            
    def _write_import_directory(self, f: BinaryIO):
        """Writes the import directory"""
        # Import Directory Table
        for dll_name, functions in self.imports.items():
            # Import Directory Entry
            f.write(struct.pack('<I', 0))  # OriginalFirstThunk
            f.write(struct.pack('<I', 0))  # TimeDateStamp
            f.write(struct.pack('<I', 0))  # ForwarderChain
            f.write(struct.pack('<I', 0))  # Name RVA
            f.write(struct.pack('<I', 0))  # FirstThunk
            
            # Import Lookup Table
            for func_name in functions:
                f.write(struct.pack('<Q', 0))  # Hint/Name RVA
                
            # NULL terminator
            f.write(struct.pack('<Q', 0))
            
        # NULL terminator for Import Directory
        f.write(bytes(20))
        
    def _calculate_image_size(self) -> int:
        """Calculates total size of image in memory"""
        size = 0
        for section in self.sections:
            section_end = section.virtual_address + section.virtual_size
            if section_end > size:
                size = section_end
        return (size + 0xFFF) & ~0xFFF  # Align to 4KB