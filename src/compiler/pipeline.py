# MetaForge Compiler - Pipeline
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
# Module: Pipeline
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Manages the pipeline of the MetaForge compiler.
#
# Key Features:
# - Lexical analysis
# - Syntax analysis
# - Code optimization
# - Semantic analysis
# - IR code generation
# - Assembly code generation
# - Creation of an executable file
#
# Usage & Extensibility:
# Can be used to create a new executable file from a MetaForge file.
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path
import time
import logging

from .parser import MetaForgeLexer, MetaForgeParser
from .diagnostics import DiagnosticEmitter, DiagnosticLevel, DiagnosticCode
from .optimization import Optimizer
from .semantic_analyzer import SemanticAnalyzer
from .ir_generator import IRGenerator
from .backend.base_backend import CompilerBackend

class CompilationStage(Enum):
    INIT = "Initialization"
    LEXICAL = "Lexical Analysis"
    PARSING = "Parsing"
    SEMANTIC = "Semantic Analysis" 
    IR_GEN = "IR Generation"
    OPTIMIZATION = "Optimization"
    NATIVE = "Native Compilation"

@dataclass
class CompilationStats:
    start_time: float
    end_time: float = 0
    tokens_count: int = 0
    ast_nodes: int = 0
    ir_instructions: int = 0
    optimizations_applied: int = 0
    warnings_count: int = 0
    errors_count: int = 0

class CompilationContext:
    def __init__(self, source_file: Path, output_file: Path, options: Dict):
        self.source_file = source_file
        self.output_file = output_file
        self.options = options
        self.stats = CompilationStats(time.time())
        self.current_stage = CompilationStage.INIT
        
    def update_stage(self, stage: CompilationStage):
        self.current_stage = stage
        logging.info(f"Entering stage: {stage.value}")

class CompilationPipeline:
    def __init__(self, diagnostic: DiagnosticEmitter, backend: CompilerBackend):
        self.diagnostic = diagnostic
        self.backend = backend
        self.optimizer = Optimizer()
        self.semantic_analyzer = SemanticAnalyzer()
        self.ir_generator = IRGenerator()
        
    def compile(self, context: CompilationContext) -> bool:
        try:
            logging.info(f"Starting compilation of {context.source_file}")
            
            # Lexical analysis
            context.update_stage(CompilationStage.LEXICAL)
            logging.debug("Reading source file...")
            source = context.source_file.read_text(encoding='utf-8')
            logging.debug(f"Source code:\n{source}")
            
            logging.debug("Creating lexer...")
            lexer = MetaForgeLexer(source)
            logging.debug("Tokenizing...")
            tokens = lexer.tokenize()
            context.stats.tokens_count = len(tokens)
            logging.debug(f"Generated {len(tokens)} tokens:")
            for token in tokens:
                logging.debug(f"  {token}")
            
            # Parsing
            context.update_stage(CompilationStage.PARSING)
            logging.debug("Creating parser...")
            parser = MetaForgeParser(tokens)
            logging.debug("Parsing tokens...")
            ast = parser.parse()
            context.stats.ast_nodes = len(ast.get('declarations', []))
            logging.debug(f"Generated AST with {context.stats.ast_nodes} nodes:")
            logging.debug(f"{ast}")
            
            # Semantic analysis
            context.update_stage(CompilationStage.SEMANTIC)
            logging.debug("Running semantic analysis...")
            if not self.semantic_analyzer.analyze(ast):
                for error in self.semantic_analyzer.errors:
                    self.diagnostic.emit_error(
                        message=error,
                        file=context.source_file,
                        code=DiagnosticCode.TYPE_ERROR
                    )
                return False
            logging.debug("Semantic analysis completed successfully")
                
            # IR Generation
            context.update_stage(CompilationStage.IR_GEN)
            logging.debug("Generating IR...")
            ir = self.ir_generator.generate(ast)
            context.stats.ir_instructions = sum(len(func.get('instructions', [])) 
                                             for func in ir.get('functions', {}).values())
            logging.debug(f"Generated IR with {context.stats.ir_instructions} instructions:")
            logging.debug(f"{ir}")
            
            if context.options.get('dump_ir'):
                self._dump_ir(ir, context.output_file.with_suffix('.ir'))
            
            # Optimization
            context.update_stage(CompilationStage.OPTIMIZATION)
            logging.debug("Running optimizations...")
            ir = self.optimizer.optimize(ir)
            context.stats.optimizations_applied = len(self.optimizer.applied_passes)
            logging.info(f"Applied {context.stats.optimizations_applied} optimizations")
            
            # Native compilation
            context.update_stage(CompilationStage.NATIVE)
            logging.info(f"Compiling to native code using {self.backend.__class__.__name__}")
            if not self.backend.compile(ir, context.output_file):
                self.diagnostic.emit_error(
                    message="Native compilation failed",
                    file=context.source_file,
                    code=DiagnosticCode.COMPILATION_ERROR
                )
                return False
                
            # Finalize
            context.stats.end_time = time.time()
            duration = context.stats.end_time - context.stats.start_time
            logging.info(f"Compilation completed in {duration:.2f}s")
            
            self._print_compilation_summary(context)
            return True
            
        except Exception as e:
            logging.error(f"Compilation failed at stage {context.current_stage.value}: {str(e)}", exc_info=True)
            self.diagnostic.emit_error(
                message=f"Compilation failed: {str(e)}",
                file=context.source_file,
                code=DiagnosticCode.COMPILATION_ERROR
            )
            return False
            
    def _dump_ir(self, ir: Dict, output_file: Path):
        """Dump IR to file for debugging"""
        logging.debug(f"Dumping IR to {output_file}")
        with open(output_file, 'w') as f:
            f.write("IR Dump:\n\n")
            
            # Dump init code
            if 'init' in ir:
                f.write("Initialization code:\n")
                for instr in ir['init']:
                    f.write(f"  {instr}\n")
                f.write("\n")
                
            # Dump functions
            for name, func in ir.get('functions', {}).items():
                f.write(f"Function {name}:\n")
                for instr in func.get('instructions', []):
                    f.write(f"  {instr}\n")
                f.write("\n")
                
            # Dump strings
            if 'strings' in ir:
                f.write("String literals:\n")
                for label, string in ir['strings'].items():
                    f.write(f"  {label}: {string}\n")
                    
    def _print_compilation_summary(self, context: CompilationContext):
        """Print compilation statistics"""
        stats = context.stats
        logging.info("Compilation Summary:")
        logging.info(f"  Source: {context.source_file}")
        logging.info(f"  Output: {context.output_file}")
        logging.info(f"  Tokens: {stats.tokens_count}")
        logging.info(f"  AST Nodes: {stats.ast_nodes}")
        logging.info(f"  IR Instructions: {stats.ir_instructions}")
        logging.info(f"  Optimizations: {stats.optimizations_applied}")
        logging.info(f"  Warnings: {stats.warnings_count}")
        logging.info(f"  Errors: {stats.errors_count}")
        logging.info(f"  Time: {stats.end_time - stats.start_time:.2f}s")