# MetaForge Compiler - Native Compiler
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
# Module: Native Compiler
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Handles native code compilation
#
# Key Features:
# - Compile C code using clang
# - Create a Windows executable
#
# Usage & Extensibility:
# This module can be used to compile C code for any platform.
# It is extensible and can be modified to support different compilers.
#
# ---------------------------------------------------------------------------------
from typing import List, Optional
import subprocess
from pathlib import Path
import os
import logging

class Architecture(Enum):
    X86 = "x86"
    X64 = "x64"
    ARM = "arm"
    ARM64 = "arm64"

class Platform(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"

class NativeCompiler:
    """Handles native code compilation"""
    
    def __init__(self, 
                 arch: Architecture = Architecture.X64,
                 platform: Platform = Platform.WINDOWS):
        self.arch = arch
        self.platform = platform
        self.vs_path = self._find_visual_studio()
        self.windows_sdk = self._find_windows_sdk()
        
    def _find_visual_studio(self) -> Optional[Path]:
        """Find Visual Studio installation"""
        possible_paths = [
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community"),
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Professional"), 
            Path(r"C:\Program Files\Microsoft Visual Studio\2022\Enterprise"),
            Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community"),
            Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Professional"),
            Path(r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise"),
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        return None
        
    def _find_windows_sdk(self) -> Optional[Path]:
        """Find Windows SDK"""
        sdk_path = Path(r"C:\Program Files (x86)\Windows Kits\10")
        if not sdk_path.exists():
            return None
            
        # Find latest version
        include_path = sdk_path / "Include"
        if not include_path.exists():
            return None
            
        versions = [x for x in include_path.iterdir() if x.is_dir()]
        if not versions:
            return None
            
        return sdk_path / "Include" / sorted(versions)[-1].name
        
    def compile(self,
                source_file: Path,
                output_file: Path,
                optimization_level: str = "-O2",
                debug: bool = False) -> bool:
        """Compile C code to native code"""
        
        try:
            # Verify source file exists
            if not source_file.exists():
                raise FileNotFoundError(f"Source file not found: {source_file}")
                
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Choose appropriate compiler
            if self.platform == Platform.WINDOWS:
                return self._compile_msvc(source_file, output_file, optimization_level, debug)
            else:
                return self._compile_gcc(source_file, output_file, optimization_level, debug)
                
        except Exception as e:
            print(f"Native compilation error: {str(e)}")
            return False
            
    def _compile_msvc(self,
                      source_file: Path,
                      output_file: Path, 
                      optimization_level: str,
                      debug: bool) -> bool:
        """Compile using MSVC"""
        
        if not self.vs_path:
            raise RuntimeError("Visual Studio not found")
            
        # Setup MSVC environment
        vcvars_path = self.vs_path / "VC" / "Auxiliary" / "Build" / "vcvars64.bat"
        if not vcvars_path.exists():
            raise RuntimeError(f"vcvars64.bat not found at {vcvars_path}")
            
        # Create temporary batch file that:
        # 1. Sets up environment
        # 2. Runs compiler
        batch_file = output_file.parent / "compile.bat"
        
        # Build cl.exe command
        cl_args = [
            "cl.exe",
            "/nologo",  # No banner
            "/W4",      # Warning level 4
            "/WX-",     # Warnings not as errors
        ]
        
        # Optimizations
        if optimization_level == "-O2":
            cl_args.extend(["/O2", "/GL"])  # Max optimization + Link-time code gen
        elif optimization_level == "-Os":
            cl_args.extend(["/O1", "/GL"])  # Min size + Link-time code gen
            
        # Debug info
        if debug:
            cl_args.extend(["/Zi", "/DEBUG"])
            
        # Include paths
        if self.windows_sdk:
            cl_args.extend([
                f'/I"{self.windows_sdk / "ucrt"}"',
                f'/I"{self.windows_sdk / "um"}"',
                f'/I"{self.windows_sdk / "shared"}"'
            ])
            
        # Output
        cl_args.extend([
            f"/Fe:{output_file}",  # Exe name
            f"/Fo:{output_file.parent / output_file.stem}.obj",  # Obj name
            f"/Tc{source_file}"  # Specify C file
        ])
        
        # Write batch file
        with open(batch_file, 'w') as f:
            f.write('@echo off\n')
            f.write(f'call "{vcvars_path}"\n')
            f.write(' '.join(cl_args))
            f.write('\n')
        
        # Run batch file
        try:
            logging.info(f"Running compiler via {batch_file}")
            
            result = subprocess.run(
                [str(batch_file)],
                capture_output=True,
                text=True,
                check=False  # Don't raise exceptions for compilation errors
            )
            
            # Log output
            if result.stdout:
                logging.info(result.stdout)
            if result.stderr:
                logging.warning(result.stderr)
                
            # Clean up temp files
            try:
                batch_file.unlink()
            except:
                pass
                
            return result.returncode == 0
            
        except Exception as e:
            logging.error(f"Failed to run compiler: {str(e)}")
            return False
            
    def _compile_gcc(self,
                     source_file: Path,
                     output_file: Path,
                     optimization_level: str,
                     debug: bool) -> bool:
        """Compile using GCC"""
        
        cmd = ["gcc"]
        
        # Architecture
        if self.arch == Architecture.X64:
            cmd.extend(["-m64"])
        elif self.arch == Architecture.X86:
            cmd.extend(["-m32"])
            
        # Optimizations
        cmd.append(optimization_level)
        
        # Debug info
        if debug:
            cmd.append("-g")
            
        # Output
        cmd.extend([
            "-o", str(output_file),
            str(source_file)
        ])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Log output
            if result.stdout:
                logging.info(result.stdout)
            if result.stderr:
                logging.warning(result.stderr)
                
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"Compilation failed: {e.stderr}")
            return False