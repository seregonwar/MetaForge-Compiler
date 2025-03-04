"""
MetaForge Compiler Package
"""

from .main import MetaForgeCompiler
from .diagnostics import DiagnosticEmitter
from .syntax_manager import MultiSyntaxManager
from .semantic_analyzer import SemanticAnalyzer
from .ir_generator import IRGenerator
from .optimization import Optimizer
from .memory.hybrid_allocator import HybridAllocator

__version__ = "0.1.0"
