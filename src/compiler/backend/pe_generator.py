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
        """Adds the export section if needed"""
        pass  # Not needed for now
        
    def _add_relocation_section(self):
        """Adds the relocation section if needed"""
        pass  # Not needed for now