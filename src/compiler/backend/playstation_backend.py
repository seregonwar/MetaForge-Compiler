from .base_backend import CompilerBackend, Platform, Architecture, BinaryFormat, BackendOptions
from typing import Dict, List, BinaryIO, Optional
from pathlib import Path
import struct
import os
import subprocess
from enum import Enum

class PSExecutableType(Enum):
    PRX = "prx"    # PlayStation Relocatable Executable
    SELF = "self"  # Signed ELF (PS4/PS5)
    SFO = "sfo"    # System File Object
    PKG = "pkg"    # Package File

class PlayStationHeader:
    """Header for PlayStation executables"""
    def __init__(self, arch: Architecture, exe_type: PSExecutableType):
        self.magic = {
            PSExecutableType.PRX: 0x7E505358,   # ~PSX
            PSExecutableType.SELF: 0x53434500,  # SCE\0
            PSExecutableType.PKG: 0x7F434E54    # CNT
        }[exe_type]
        
        self.version = {
            Architecture.X64: 0x0004,  # PS4/PS5
            Architecture.ARM64: 0x0005 # PS5
        }[arch]
        
        self.flags = 0x0002  # Executable
        self.sdk_type = 0x0001  # Retail
        self.category = 0x0001  # Game
        self.content_id = b'\0' * 32  # 32-byte content ID
        
class PlayStationBackend(CompilerBackend):
    """Backend for generating PlayStation executables"""
    
    def __init__(self, options: BackendOptions):
        super().__init__(options)
        self.sdk_path = self._find_playstation_sdk()
        self.toolchain = self._setup_toolchain()
        
    def _find_playstation_sdk(self) -> Optional[Path]:
        """Finds installed PlayStation SDK"""
        possible_paths = [
            Path("/usr/local/playstation/sdk"),
            Path("C:/Program Files/PlayStation/SDK"),
            Path(os.environ.get("PS_SDK_PATH", ""))
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
        
    def _setup_toolchain(self) -> Dict:
        """Sets up PlayStation toolchain"""
        if not self.sdk_path:
            raise RuntimeError("PlayStation SDK not found")
            
        return {
            'compiler': self.sdk_path / "bin" / "orbis-clang",
            'linker': self.sdk_path / "bin" / "orbis-ld",
            'tools': {
                'make_fself': self.sdk_path / "bin" / "make_fself",
                'create_pkg': self.sdk_path / "bin" / "create-pkg",
                'sign_pkg': self.sdk_path / "bin" / "sign-pkg"
            },
            'libs': self.sdk_path / "target/lib",
            'includes': self.sdk_path / "target/include"
        }
        
    def compile(self, ir: Dict, output_file: Path) -> bool:
        try:
            # Generate sections
            text_section = self._generate_text_section(ir)
            data_section = self._generate_data_section(ir)
            
            # Create PlayStation header
            ps_header = PlayStationHeader(
                self.options.architecture,
                PSExecutableType.SELF
            )
            
            # Generate base executable
            elf_file = output_file.with_suffix('.elf')
            if not self._generate_elf(text_section, data_section, elf_file):
                return False
                
            # Convert to SELF (PS4/PS5 executable)
            if not self._convert_to_self(elf_file, output_file):
                return False
                
            # Create package if requested
            if self.options.create_pkg:
                pkg_file = output_file.with_suffix('.pkg')
                if not self._create_package(output_file, pkg_file):
                    return False
                    
            return True
            
        except Exception as e:
            print(f"Error generating PlayStation executable: {str(e)}")
            return False
            
    def _generate_elf(self, text: bytes, data: bytes, output: Path) -> bool:
        """Generates base ELF file"""
        try:
            # Compile using orbis-clang
            cmd = [
                str(self.toolchain['compiler']),
                '-target', 'x86_64-scei-ps4' if self.options.architecture == Architecture.X64 else 'aarch64-scei-ps5',
                '-fPIC',
                '-O2',
                '-I', str(self.toolchain['includes']),
                '-o', str(output)
            ]
            
            if self.options.debug_info:
                cmd.append('-g')
                
            # Add PlayStation libraries
            cmd.extend([
                '-L', str(self.toolchain['libs']),
                '-lSceLibc',
                '-lSceSystemService',
                '-lSceUserService'
            ])
            
            return subprocess.run(cmd, check=True).returncode == 0
            
        except Exception as e:
            print(f"ELF generation failed: {str(e)}")
            return False
            
    def _convert_to_self(self, elf_file: Path, output: Path) -> bool:
        """Converts ELF to signed SELF"""
        try:
            cmd = [
                str(self.toolchain['tools']['make_fself']),
                '--paid', '0x3800000000000011',  # Game application
                str(elf_file),
                str(output)
            ]
            
            return subprocess.run(cmd, check=True).returncode == 0
            
        except Exception as e:
            print(f"SELF conversion failed: {str(e)}")
            return False
            
    def _create_package(self, self_file: Path, output: Path) -> bool:
        """Creates PlayStation package"""
        try:
            # Generate SFO
            sfo_file = self_file.with_suffix('.sfo')
            self._generate_sfo(sfo_file)
            
            # Create PKG
            cmd = [
                str(self.toolchain['tools']['create_pkg']),
                '--content-id', 'IV0000-ABCD12345_00-0123456789ABCDEF',
                '--sfo', str(sfo_file),
                '--self', str(self_file),
                '--out', str(output)
            ]
            
            if not subprocess.run(cmd, check=True).returncode == 0:
                return False
                
            # Sign PKG
            cmd = [
                str(self.toolchain['tools']['sign_pkg']),
                str(output)
            ]
            
            return subprocess.run(cmd, check=True).returncode == 0
            
        except Exception as e:
            print(f"Package creation failed: {str(e)}")
            return False
            
    def _generate_sfo(self, output: Path):
        """Generates SFO metadata file"""
        sfo_data = {
            'APP_VER': '01.00',
            'CATEGORY': 'gd',
            'CONTENT_ID': 'IV0000-ABCD12345_00-0123456789ABCDEF',
            'TITLE': 'MetaForge Application',
            'TITLE_ID': 'ABCD12345',
            'VERSION': '01.00'
        }
        
        # Write SFO header
        with open(output, 'wb') as f:
            # Magic "\0PSF"
            f.write(b'\0PSF')
            # Version 1.1
            f.write(struct.pack('<I', 0x101))
            # Key table start
            key_table_start = 20
            f.write(struct.pack('<I', key_table_start))
            # Data table start 
            data_table_start = key_table_start + sum(len(k) + 1 for k in sfo_data.keys())
            f.write(struct.pack('<I', data_table_start))
            # Number of entries
            f.write(struct.pack('<I', len(sfo_data)))
            
            # Write key table
            offset = 0
            for key in sfo_data.keys():
                # Key offset
                f.write(struct.pack('<H', offset))
                # Data format (UTF-8 string)
                f.write(struct.pack('<H', 0x0204))
                # Length of value
                f.write(struct.pack('<I', len(sfo_data[key])))
                # Max length (same as length for fixed strings)
                f.write(struct.pack('<I', len(sfo_data[key])))
                # Data offset
                f.write(struct.pack('<I', offset))
                
                offset += len(sfo_data[key])
                
            # Write keys
            for key in sfo_data.keys():
                f.write(key.encode('utf-8') + b'\0')
                
            # Write values
            for value in sfo_data.values():
                f.write(value.encode('utf-8'))
        
    def supports_platform(self, platform: Platform) -> bool:
        return platform == Platform.PLAYSTATION
        
    def supports_architecture(self, arch: Architecture) -> bool:
        return arch in [Architecture.X64, Architecture.ARM64]  # PS4 = x64, PS5 = x64/ARM64
        
    def get_file_extension(self) -> str:
        return ".self"