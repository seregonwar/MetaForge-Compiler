# MetaForge Compiler - Build System
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
# Module: Build System
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# This module is part of the MetaForge Compiler, a compiler for the
# MetaForge programming language.
# The module provides a build system for MetaForge, which is responsible
# for building and linking MetaForge programs.
#
# Key Features:
# - Building and linking MetaForge programs
# - Generating executables and libraries
# - Supporting multiple platforms and architectures
#
# Usage & Extensibility:
# The build system is used to build and link MetaForge programs. It can be
# extended to support additional platforms and architectures.
#
# ---------------------------------------------------------------------------------
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional, Set
from pathlib import Path
import subprocess
import json
import os
import struct

from .base_backend import Platform, Architecture, BinaryFormat, BackendOptions
from .x64_assembler import X64Assembler
from ..diagnostics import DiagnosticEmitter
from .coff_parser import CoffParser, SectionFlags
from .lib_parser import LibraryParser

class BuildType(Enum):
    DEBUG = "debug"
    RELEASE = "release" 
    RELEASE_WITH_DEBUG = "relwithdebinfo"
    MINIMUM_SIZE = "minsize"

@dataclass
class BuildTarget:
    name: str
    sources: List[Path]
    includes: List[Path]
    defines: Dict[str, str]
    libraries: List[str]
    output_type: str  # exe/lib/dll
    output_name: str
    dependencies: List[str] = None

class BuildSystem:
    """Advanced build system for MetaForge"""
    
    def __init__(self, 
                 diagnostic: DiagnosticEmitter,
                 build_dir: Path,
                 options: BackendOptions):
        self.diagnostic = diagnostic
        self.build_dir = build_dir
        self.options = options
        self.targets: Dict[str, BuildTarget] = {}
        self.built_targets: Set[str] = set()
        self.assembler = X64Assembler()
        
    def add_target(self, target: BuildTarget):
        """Add a build target"""
        self.targets[target.name] = target
        
    def build(self, target_name: str) -> bool:
        """Build a target and its dependencies"""
        if target_name in self.built_targets:
            return True
            
        target = self.targets.get(target_name)
        if not target:
            self.diagnostic.emit_error(
                message=f"Unknown build target: {target_name}",
                file=Path("build.mf")
            )
            return False
            
        # Build dependencies first
        if target.dependencies:
            for dep in target.dependencies:
                if not self.build(dep):
                    return False
                    
        # Create build directory for target
        target_build_dir = self.build_dir / target_name
        target_build_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate build config
        config = self._generate_build_config(target, target_build_dir)
        
        # Write build config
        config_file = target_build_dir / "build.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
            
        # Build target
        success = self._build_target(target, target_build_dir, config)
        if success:
            self.built_targets.add(target_name)
            
        return success
        
    def _generate_build_config(self, target: BuildTarget, build_dir: Path) -> Dict:
        """Generate build configuration"""
        return {
            'name': target.name,
            'type': target.output_type,
            'output': str(build_dir / target.output_name),
            'sources': [str(s) for s in target.sources],
            'includes': [str(i) for i in target.includes],
            'defines': target.defines,
            'libraries': target.libraries,
            'platform': self.options.platform.value,
            'architecture': self.options.architecture.value,
            'binary_format': self.options.binary_format.value,
            'debug_info': self.options.debug_info,
            'pic': self.options.pic,
            'optimize_level': self.options.optimize_level,
            'target_cpu': self.options.target_cpu,
            'cpu_features': self.options.cpu_features
        }
        
    def _build_target(self, target: BuildTarget, build_dir: Path, config: Dict) -> bool:
        """Execute actual build of a target"""
        try:
            # Compile each source file
            objects = []
            for source in target.sources:
                obj_file = build_dir / f"{source.stem}.o"
                if self._compile_source(source, obj_file, config):
                    objects.append(obj_file)
                else:
                    return False
                    
            # Link
            output_file = Path(config['output'])
            return self._link(objects, output_file, config)
            
        except Exception as e:
            self.diagnostic.emit_error(
                message=f"Build failed: {str(e)}",
                file=Path("build.mf")
            )
            return False
            
    def _compile_source(self, source: Path, output: Path, config: Dict) -> bool:
        """Compile a single source file"""
        try:
            # Parse source to IR
            ir = self._parse_to_ir(source)
            
            # Generate native code
            if config['architecture'] == 'x64':
                code = self.assembler.assemble(ir['instructions'])
            else:
                raise NotImplementedError(f"Architecture {config['architecture']} not supported yet")
                
            # Write object file
            self._write_object_file(code, output, config)
            return True
            
        except Exception as e:
            self.diagnostic.emit_error(
                message=f"Compilation failed: {str(e)}",
                file=source
            )
            return False
            
    def _link(self, objects: List[Path], output: Path, config: Dict) -> bool:
        """Link object files"""
        try:
            if config['platform'] == 'windows':
                return self._link_windows(objects, output, config)
            elif config['platform'] == 'linux':
                return self._link_linux(objects, output, config)
            elif config['platform'] == 'macos':
                return self._link_macos(objects, output, config)
            else:
                raise ValueError(f"Unsupported platform: {config['platform']}")
                
        except Exception as e:
            self.diagnostic.emit_error(
                message=f"Linking failed: {str(e)}",
                file=output
            )
            return False
            
    def _link_windows(self, objects: List[Path], output: Path, config: Dict) -> bool:
        """Link for Windows using link.exe"""
        cmd = ['link.exe', '/nologo']
        
        # Debug info
        if config['debug_info']:
            cmd.extend(['/DEBUG'])
            
        # Output
        cmd.extend([f'/OUT:{output}'])
        
        # Objects
        cmd.extend(str(obj) for obj in objects)
        
        # Libraries
        cmd.extend(config['libraries'])
        
        return subprocess.run(cmd, check=True).returncode == 0
        
    def _link_linux(self, objects: List[Path], output: Path, config: Dict) -> bool:
        """Link for Linux using ld"""
        cmd = ['ld']
        
        # Output
        cmd.extend(['-o', str(output)])
        
        # Objects
        cmd.extend(str(obj) for obj in objects)
        
        # Libraries
        for lib in config['libraries']:
            if lib.startswith('-l'):
                cmd.append(lib)
            else:
                cmd.append(f'-l{lib}')
                
        return subprocess.run(cmd, check=True).returncode == 0
        
    def _link_macos(self, objects: List[Path], output: Path, config: Dict) -> bool:
        """Link for macOS using ld"""
        cmd = ['ld']
        
        # Platform specific
        cmd.extend(['-platform_version', 'macos', '11.0', '11.0'])
        
        # Output
        cmd.extend(['-o', str(output)])
        
        # Objects
        cmd.extend(str(obj) for obj in objects)
        
        # System libraries
        cmd.extend([
            '-lSystem',
            '-syslibroot', '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk'
        ])
        
        # User libraries
        for lib in config['libraries']:
            if lib.startswith('-l'):
                cmd.append(lib)
            else:
                cmd.append(f'-l{lib}')
                
        return subprocess.run(cmd, check=True).returncode == 0
        
    def _parse_to_ir(self, source: Path) -> Dict:
        """Parse source file to IR"""
        with open(source, 'r') as f:
            content = f.read()
            
        # Basic IR structure
        return {
            'instructions': [],
            'data': [],
            'symbols': {},
            'relocations': []
        }
        
    def _write_object_file(self, code: bytes, output: Path, config: Dict):
        """Write object file in appropriate format"""
        if config['binary_format'] == 'pe':
            self._write_coff_object(code, output)
        elif config['binary_format'] == 'elf':
            self._write_elf_object(code, output)
        elif config['binary_format'] == 'mach-o':
            self._write_macho_object(code, output)
        else:
            raise ValueError(f"Unsupported binary format: {config['binary_format']}")
            
    def _write_coff_object(self, code: bytes, output: Path):
        """Write COFF object file"""
        with open(output, 'wb') as f:
            # Write COFF header
            f.write(struct.pack('<HHIIIHH',
                0x8664,  # Machine (x64)
                1,       # Number of sections
                0,       # Timestamp
                0,       # Symbol table offset
                0,       # Number of symbols
                0,       # Optional header size
                0x0     # Characteristics
            ))
            
            # Write section header
            f.write(struct.pack('<8sIIIIIIHHI',
                b'.text\0\0\0',  # Name
                len(code),       # Virtual size
                0,              # Virtual address
                len(code),      # Raw data size
                0x40,           # Raw data pointer
                0,              # Relocations pointer
                0,              # Line numbers pointer
                0,              # Number of relocations
                0,              # Number of line numbers
                SectionFlags.TEXT.value  # Characteristics
            ))
            
            # Write section data
            f.write(code)
            
    def _write_elf_object(self, code: bytes, output: Path):
        """Write ELF object file"""
        with open(output, 'wb') as f:
            # ELF header
            f.write(bytes([0x7f, 0x45, 0x4c, 0x46]))  # Magic
            f.write(bytes([
                2,    # 64-bit
                1,    # Little endian
                1,    # Version
                0,    # System V ABI
                0,    # ABI version
                0, 0, 0, 0, 0, 0, 0  # Padding
            ]))
            
            # Write code section
            f.write(code)
            
    def _write_macho_object(self, code: bytes, output: Path):
        """Write Mach-O object file"""
        with open(output, 'wb') as f:
            # Mach-O header
            f.write(struct.pack('<I', 0xfeedfacf))  # Magic (64-bit)
            f.write(struct.pack('<II',
                0x01000007,  # CPU type (x64)
                0x80000003   # CPU subtype (all)
            ))
            
            # Write code section
            f.write(code)