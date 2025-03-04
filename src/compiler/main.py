import sys
import os
import logging
from typing import List, Optional

from src.compiler.diagnostics import DiagnosticEmitter
from src.compiler.syntax_manager import MultiSyntaxManager
from src.compiler.semantic_analyzer import SemanticAnalyzer
from src.compiler.ir_generator import IRGenerator
from src.compiler.optimization import Optimizer
from src.compiler.memory.hybrid_allocator import HybridAllocator

class MetaForgeCompiler:
    def __init__(self):
        self.diagnostics = DiagnosticEmitter()
        self.syntax_manager = MultiSyntaxManager()
        self.semantic_analyzer = SemanticAnalyzer(self.diagnostics)
        self.ir_generator = IRGenerator()
        self.optimizer = Optimizer()
        self.memory_manager = HybridAllocator()
        
        logging.basicConfig(level=logging.DEBUG)  
        self.logger = logging.getLogger("MetaForge")
        
    def compile_file(self, source_file: str, output_file: Optional[str] = None) -> bool:
        """Compile a single source file"""
        try:
            self.logger.debug(f"Starting compilation of {source_file}")
            
            # Read source file
            self.logger.debug("Reading source file...")
            with open(source_file, 'r') as f:
                source = f.read()
            self.logger.debug(f"Source file read, size: {len(source)} bytes")
                
            # Determine output file
            if output_file is None:
                base = os.path.splitext(source_file)[0]
                output_file = f"{base}.exe"
            self.logger.debug(f"Output file will be: {output_file}")
                
            # Parse and compile
            self.logger.debug("Starting parsing...")
            ast = self.syntax_manager.parse(source)
            if not ast:
                self.logger.error(f"Failed to parse {source_file}")
                return False
            self.logger.debug("Parsing completed successfully")
                
            # Semantic analysis
            self.logger.debug("Starting semantic analysis...")
            if not self.semantic_analyzer.analyze(ast):
                self.logger.error(f"Semantic analysis failed for {source_file}")
                return False
            self.logger.debug("Semantic analysis completed successfully")
                
            # Generate IR
            self.logger.debug("Starting IR generation...")
            ir = self.ir_generator.generate(ast)
            if not ir:
                self.logger.error(f"IR generation failed for {source_file}")
                return False
            self.logger.debug("IR generation completed successfully")
                
            # Optimize
            self.logger.debug("Starting optimization...")
            optimized_ir = self.optimizer.optimize(ir)
            self.logger.debug("Optimization completed successfully")
            
            # Generate code
            self.logger.debug("Starting code generation...")
            if not self.generate_code(optimized_ir, output_file):
                self.logger.error(f"Code generation failed for {source_file}")
                return False
            self.logger.debug("Code generation completed successfully")
                
            self.logger.info(f"Successfully compiled {source_file} to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Compilation error: {str(e)}")
            import traceback
            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
            
    def generate_code(self, ir, output_file: str) -> bool:
        """Generate executable code from IR"""
        # TODO: Implement actual code generation
        self.logger.info("Code generation not yet implemented")
        return True

def main():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("MetaForge-Main")
    
    logger.debug("Starting MetaForge compiler...")
    
    if len(sys.argv) < 2:
        logger.error("No source file provided")
        print("Usage: metaforge <source_file> [output_file]")
        sys.exit(1)
        
    source_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    logger.debug(f"Source file: {source_file}")
    logger.debug(f"Output file: {output_file}")
    
    compiler = MetaForgeCompiler()
    success = compiler.compile_file(source_file, output_file)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
