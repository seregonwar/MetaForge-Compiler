from .base_backend import CompilerBackend, Platform, Architecture, BinaryFormat, BackendOptions
from typing import Dict, List, BinaryIO
from pathlib import Path
import struct

class MachHeader:
    """Mach-O format header"""
    def __init__(self, arch: Architecture):
        self.magic = 0xFEEDFACF if arch in [Architecture.X64, Architecture.ARM64] else 0xFEEDFACE
        self.cputype = {
            Architecture.X86: 0x7,     # CPU_TYPE_X86
            Architecture.X64: 0x1000007,# CPU_TYPE_X86_64
            Architecture.ARM: 0xC,     # CPU_TYPE_ARM
            Architecture.ARM64: 0x100000C # CPU_TYPE_ARM64
        }[arch]
        self.cpusubtype = 0x3 if arch == Architecture.X86 else 0x0
        self.filetype = 0x2  # MH_EXECUTE
        self.ncmds = 0
        self.sizeofcmds = 0
        self.flags = 0x85
        self.reserved = 0 if arch in [Architecture.X64, Architecture.ARM64] else None

class MacOSBackend(CompilerBackend):
    """Backend for generating macOS executables (Mach-O)"""
    
    def compile(self, ir: Dict, output_file: Path) -> bool:
        try:
            # Generate sections
            text_section = self._generate_text_section(ir)
            data_section = self._generate_data_section(ir)
            
            # Create Mach-O header
            mach_header = MachHeader(self.options.architecture)
            
            # Calculate offsets
            header_size = 32 if self.options.architecture in [Architecture.X64, Architecture.ARM64] else 28
            load_commands_size = 0  # TODO: calculate load commands size
            text_offset = header_size + load_commands_size
            data_offset = text_offset + len(text_section)
            
            # Update header
            mach_header.ncmds = 2  # LC_SEGMENT + LC_MAIN
            mach_header.sizeofcmds = load_commands_size
            
            # Write the file
            with open(output_file, 'wb') as f:
                # Write Mach-O header
                self._write_mach_header(f, mach_header)
                
                # Write load commands
                self._write_load_commands(f, text_offset, len(text_section),
                                       data_offset, len(data_section))
                                       
                # Write sections
                f.write(text_section)
                f.write(data_section)
                
            return True
            
        except Exception as e:
            print(f"Error generating Mach-O: {str(e)}")
            return False
            
    def supports_platform(self, platform: Platform) -> bool:
        return platform == Platform.MACOS
        
    def supports_architecture(self, arch: Architecture) -> bool:
        return arch in [Architecture.X64, Architecture.ARM64]
        
    def get_file_extension(self) -> str:
        return ""  # macOS executables don't need extension
        
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
        
    def _write_mach_header(self, f: BinaryIO, header: MachHeader):
        """Write Mach-O header"""
        f.write(struct.pack('>IIIIII',
            header.magic,
            header.cputype,
            header.cpusubtype,
            header.filetype,
            header.ncmds,
            header.sizeofcmds,
            header.flags
        ))
        if header.reserved is not None:
            f.write(struct.pack('>I', header.reserved))
            
    def _write_load_commands(self, f: BinaryIO,
                           text_offset: int, text_size: int,
                           data_offset: int, data_size: int):
        """Write load commands"""
        # Write LC_SEGMENT_64 command for __TEXT segment
        f.write(struct.pack('>IIII', 0x19, 72, 0, 0))  # cmd, cmdsize, segname
        f.write(struct.pack('>QQ', 0x1000, 0x2000))    # vmaddr, vmsize
        f.write(struct.pack('>QQ', text_offset, text_size)) # fileoff, filesize
        f.write(struct.pack('>II', 7, 0))              # maxprot, initprot
        f.write(struct.pack('>II', 1, 0))              # nsects, flags
        
        # Write section for __text
        f.write(b'__text\x00' * 2)                     # sectname, segname
        f.write(struct.pack('>QQ', 0x1000, text_size)) # addr, size
        f.write(struct.pack('>II', text_offset, 0))    # offset, align
        f.write(struct.pack('>III', 0, 0, 0))          # reloff, nreloc, flags
        
        # Write LC_SEGMENT_64 command for __DATA segment  
        f.write(struct.pack('>IIII', 0x19, 72, 0, 0))
        f.write(struct.pack('>QQ', 0x2000, 0x1000))
        f.write(struct.pack('>QQ', data_offset, data_size))
        f.write(struct.pack('>II', 7, 3))
        f.write(struct.pack('>II', 1, 0))
        
        # Write section for __data
        f.write(b'__data\x00' * 2)
        f.write(struct.pack('>QQ', 0x2000, data_size))
        f.write(struct.pack('>II', data_offset, 0))
        f.write(struct.pack('>III', 0, 0, 0))
        
        # Write LC_MAIN command
        f.write(struct.pack('>III', 0x80000028, 24, 0)) # cmd, cmdsize, flags
        f.write(struct.pack('>QQ', 0x1000, 0))          # entryoff, stacksize