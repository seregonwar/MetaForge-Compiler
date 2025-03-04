from typing import Dict, List, Optional
from pathlib import Path
import logging
from .base_backend import CompilerBackend, Platform, Architecture, BinaryFormat, BackendOptions
from .x64_assembler import X64Assembler, Register
from .pe_generator import PEGenerator
from .oop_generator import OOPGenerator, ClassInfo, MethodInfo

class WindowsBackend(CompilerBackend):
    def __init__(self, options: BackendOptions):
        super().__init__(options)
        self.assembler = X64Assembler()
        self.pe_gen = PEGenerator()
        self.oop_gen = OOPGenerator()
        self.current_class: Optional[ClassInfo] = None
        self.data_section = bytearray()
        self.bss_section = bytearray()
        self.vtables: Dict[str, int] = {}  # Class name to vtable offset mapping
        self.static_areas: Dict[str, int] = {}  # Class name to static area offset mapping

    def supports_platform(self, platform: Platform) -> bool:
        return platform == Platform.WINDOWS

    def supports_architecture(self, arch: Architecture) -> bool:
        return arch in [Architecture.X64, Architecture.X86]

    def get_file_extension(self) -> str:
        return ".exe" if self.options.binary_format == BinaryFormat.PE else ".dll"

    def compile(self, ir: Dict, output_file: Path) -> bool:
        if not super().compile(ir, output_file):
            return False

        try:
            # Initialize sections
            self.data_section = bytearray()
            self.bss_section = bytearray()
            self.vtables.clear()
            self.static_areas.clear()

            # Process OOP structures first
            self._process_classes(ir.get("classes", {}))
            
            # Generate code
            code = self._generate_code(ir)
            
            # Create PE file
            self.pe_gen.create_pe_file(
                output_file,
                code,
                self.data_section,
                self.bss_section,
                self.options.debug_info
            )
            
            return True
            
        except Exception as e:
            logging.error(f"Compilation failed: {str(e)}")
            return False

    def _process_classes(self, classes: Dict) -> None:
        """Process class definitions and generate vtables"""
        for class_name, class_info in classes.items():
            # Create class info
            self.current_class = ClassInfo(
                name=class_name,
                methods=class_info.get("methods", {}),
                fields=class_info.get("fields", {}),
                parent=class_info.get("parent", None),
                interfaces=class_info.get("interfaces", [])
            )

            # Generate vtable
            vtable_offset = self.oop_gen.generate_vtable(
                self.current_class,
                self.data_section
            )
            self.vtables[class_name] = vtable_offset

            # Generate static area if needed
            if self.current_class.has_static_members():
                static_offset = self.oop_gen.generate_static_area(
                    self.current_class,
                    self.bss_section
                )
                self.static_areas[class_name] = static_offset

    def _generate_code(self, ir: Dict) -> bytearray:
        """Generate machine code from IR"""
        code = bytearray()
        
        # Generate entry point
        if "main" in ir:
            self._generate_entry_point(code)
            
        # Generate method implementations
        for class_name, class_info in ir.get("classes", {}).items():
            self.current_class = ClassInfo(
                name=class_name,
                methods=class_info.get("methods", {}),
                fields=class_info.get("fields", {}),
                parent=class_info.get("parent", None),
                interfaces=class_info.get("interfaces", [])
            )
            
            for method_name, method_info in class_info.get("methods", {}).items():
                self._generate_method(
                    code,
                    MethodInfo(
                        name=method_name,
                        params=method_info.get("params", []),
                        return_type=method_info.get("return_type", "void"),
                        is_static=method_info.get("is_static", False),
                        is_virtual=method_info.get("is_virtual", False),
                        body=method_info.get("body", [])
                    )
                )
                
        return code

    def _generate_entry_point(self, code: bytearray) -> None:
        """Generate entry point code"""
        # Standard Windows x64 entry point
        self.assembler.generate_prolog(code)
        self.assembler.mov(code, Register.RCX, Register.RCX)  # Preserve args
        self.assembler.call(code, "main")
        self.assembler.generate_epilog(code)

    def _generate_method(self, code: bytearray, method: MethodInfo) -> None:
        """Generate code for a method"""
        # Method prolog
        self.assembler.generate_prolog(code)
        
        # Generate method body
        for instruction in method.body:
            self.assembler.generate_instruction(code, instruction)
            
        # Method epilog
        self.assembler.generate_epilog(code)