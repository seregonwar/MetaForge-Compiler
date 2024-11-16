from .base_backend import CompilerBackend, Platform, Architecture, BinaryFormat, BackendOptions
from typing import Dict, List, BinaryIO
from pathlib import Path
import struct

class ElfHeader:
    """ELF format header"""
    def __init__(self, arch: Architecture):
        self.e_ident = bytes([
            0x7F, 0x45, 0x4C, 0x46,  # Magic number
            0x02 if arch in [Architecture.X64, Architecture.ARM64] else 0x01,  # Class
            0x01,  # Data (little endian)
            0x01,  # Version
            0x00,  # OS ABI
            0x00,  # ABI Version
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00  # Padding
        ])
        self.e_type = 0x0002  # ET_EXEC
        self.e_machine = {
            Architecture.X86: 0x03,    # EM_386
            Architecture.X64: 0x3E,    # EM_X86_64
            Architecture.ARM: 0x28,    # EM_ARM
            Architecture.ARM64: 0xB7    # EM_AARCH64
        }[arch]
        self.e_version = 0x01
        self.e_entry = 0  # Entry point
        self.e_phoff = 64  # Program header offset
        self.e_shoff = 0  # Section header offset
        self.e_flags = 0
        self.e_ehsize = 64
        self.e_phentsize = 56
        self.e_phnum = 0
        self.e_shentsize = 64
        self.e_shnum = 0
        self.e_shstrndx = 0

class LinuxBackend(CompilerBackend):
    """Backend for generating Linux executables (ELF)"""
    
    def compile(self, ir: Dict, output_file: Path) -> bool:
        try:
            # Generate sections
            text_section = self._generate_text_section(ir)
            data_section = self._generate_data_section(ir)
            
            # Create ELF header
            elf_header = ElfHeader(self.options.architecture)
            
            # Calculate offsets
            text_offset = 64 + elf_header.e_phentsize * 2  # Header + 2 program headers
            data_offset = text_offset + len(text_section)
            
            # Update header
            elf_header.e_entry = text_offset  # Entry point at start of code
            elf_header.e_phnum = 2  # Two program headers (text and data)
            
            # Write the file
            with open(output_file, 'wb') as f:
                # Write ELF header
                self._write_elf_header(f, elf_header)
                
                # Write program headers
                self._write_program_headers(f, text_offset, len(text_section),
                                         data_offset, len(data_section))
                                         
                # Write sections
                f.write(text_section)
                f.write(data_section)
                
            return True
            
        except Exception as e:
            print(f"Error generating ELF: {str(e)}")
            return False
            
    def supports_platform(self, platform: Platform) -> bool:
        return platform == Platform.LINUX
        
    def supports_architecture(self, arch: Architecture) -> bool:
        return arch in [Architecture.X86, Architecture.X64, 
                       Architecture.ARM, Architecture.ARM64]
        
    def get_file_extension(self) -> str:
        return ""  # Linux executables don't need extension
        
    def _generate_text_section(self, ir: Dict) -> bytes:
        """Generate text section (code)"""
        text_data = bytearray()
        
        # Generate code for each function
        for func in ir.get('functions', []):
            # Add function prologue
            text_data.extend([
                0x55,                   # push rbp
                0x48, 0x89, 0xE5       # mov rbp, rsp
            ])
            
            # Generate code for each instruction
            for instr in func.get('instructions', []):
                if instr['type'] == 'mov':
                    text_data.extend([
                        0x48, 0xB8     # mov rax, imm64
                    ])
                    text_data.extend(struct.pack('<Q', instr['value']))
                elif instr['type'] == 'ret':
                    text_data.extend([
                        0x5D,          # pop rbp
                        0xC3           # ret
                    ])
                    
        return bytes(text_data)
        
    def _generate_data_section(self, ir: Dict) -> bytes:
        """Generate data section"""
        data = bytearray()
        
        # Add global variables
        for var in ir.get('globals', []):
            if var['type'] == 'string':
                # Add string data with null terminator
                data.extend(var['value'].encode('utf-8') + b'\0')
            elif var['type'] == 'integer':
                # Add 8-byte integer
                data.extend(struct.pack('<Q', var['value']))
                
        return bytes(data)
        
    def _write_elf_header(self, f: BinaryIO, header: ElfHeader):
        """Write ELF header"""
        f.write(header.e_ident)
        f.write(struct.pack('<HHIQQQIHHHHHH',
            header.e_type,
            header.e_machine,
            header.e_version,
            header.e_entry,
            header.e_phoff,
            header.e_shoff,
            header.e_flags,
            header.e_ehsize,
            header.e_phentsize,
            header.e_phnum,
            header.e_shentsize,
            header.e_shnum,
            header.e_shstrndx
        ))
        
    def _write_program_headers(self, f: BinaryIO, 
                             text_offset: int, text_size: int,
                             data_offset: int, data_size: int):
        """Write program headers"""
        # Text segment
        f.write(struct.pack('<IIQQQQQQ',
            0x1,        # PT_LOAD
            0x5,        # PF_R | PF_X
            text_offset, # Offset
            0x400000 + text_offset,  # Virtual address
            0x400000 + text_offset,  # Physical address
            text_size,  # Size in file
            text_size,  # Size in memory
            0x1000     # Alignment
        ))
        
        # Data segment
        f.write(struct.pack('<IIQQQQQQ',
            0x1,        # PT_LOAD
            0x6,        # PF_R | PF_W
            data_offset,# Offset
            0x600000 + data_offset,  # Virtual address
            0x600000 + data_offset,  # Physical address
            data_size,  # Size in file
            data_size,  # Size in memory
            0x1000     # Alignment
        )) 