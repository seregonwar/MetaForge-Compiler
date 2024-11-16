from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path

class Platform(Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    PLAYSTATION = "playstation"

class Architecture(Enum):
    X86 = "x86"
    X64 = "x64"
    ARM = "arm"
    ARM64 = "arm64"

class BinaryFormat(Enum):
    PE = "pe"      # Windows
    ELF = "elf"    # Linux
    MACHO = "mach-o" # macOS

@dataclass
class BackendOptions:
    platform: Platform
    architecture: Architecture
    binary_format: BinaryFormat
    debug_info: bool = False
    pic: bool = False  # Position Independent Code
    optimize_level: int = 0
    target_cpu: Optional[str] = None
    cpu_features: List[str] = None

class CompilerBackend(ABC):
    """Base class for compiler backends"""
    
    def __init__(self, options: BackendOptions):
        self.options = options
        
    @abstractmethod
    def compile(self, ir: Dict, output_file: Path) -> bool:
        """Compile IR to target binary format"""
        if not self.supports_platform(self.options.platform):
            return False
            
        if not self.supports_architecture(self.options.architecture):
            return False
            
        return True
        
    @abstractmethod
    def supports_platform(self, platform: Platform) -> bool:
        """Check if backend supports a platform"""
        return platform in [Platform.WINDOWS, Platform.LINUX, Platform.MACOS]
        
    @abstractmethod
    def supports_architecture(self, arch: Architecture) -> bool:
        """Check if backend supports an architecture"""
        return arch in [Architecture.X64, Architecture.X86]
        
    @abstractmethod
    def get_file_extension(self) -> str:
        """Get file extension for this backend"""
        if self.options.platform == Platform.WINDOWS:
            return ".obj"
        elif self.options.platform == Platform.LINUX:
            return ".o"
        elif self.options.platform == Platform.MACOS:
            return ".o"
        return ".o"