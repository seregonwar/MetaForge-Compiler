from .base_backend import CompilerBackend, Platform, Architecture, BinaryFormat, BackendOptions
from typing import Dict, List, Optional
from pathlib import Path
import logging
from .x64_assembler import X64Assembler, Register, OperandType, Operand
from .pe_generator import PEGenerator, Section

class WindowsBackend(CompilerBackend):
    """Backend for generating native Windows executables (PE)"""
    
    def __init__(self, options: BackendOptions):
        super().__init__(options)
        self.assembler = X64Assembler()
        self.pe_generator = PEGenerator()
        self.string_literals = {}
        
    def compile(self, ir: Dict, output_file: Path) -> bool:
        try:
            logging.info("Starting Windows native compilation...")
            logging.debug(f"Generating code for IR: {ir}")
            
            # Generate machine code
            logging.info("Generating machine code...")
            text_section = self._generate_text_section(ir)
            if not text_section:
                logging.error("Failed to generate text section")
                return False
                
            logging.info(f"Generated {len(text_section)} bytes of machine code")
            
            # Generate data section
            logging.info("Generating data section...")
            data_section = self._generate_data_section(ir)
            logging.info(f"Generated {len(data_section)} bytes of data")
            
            # Create PE sections
            logging.info("Creating PE sections...")
            text = Section(
                name=".text",
                virtual_address=0x1000,
                virtual_size=len(text_section),
                raw_data_size=len(text_section),
                raw_data_ptr=0,
                characteristics=0x60000020,  # CODE|EXECUTE|READ
                data=text_section
            )
            
            data = Section(
                name=".data",
                virtual_address=0x2000,
                virtual_size=len(data_section),
                raw_data_size=len(data_section),
                raw_data_ptr=0,
                characteristics=0xC0000040,  # INITIALIZED_DATA|READ|WRITE
                data=data_section
            )
            
            # Create PE generator
            logging.info("Generating PE file...")
            pe_gen = PEGenerator()
            pe_gen.entry_point = 0x1000  # Entry point at start of code
            
            # Add sections
            pe_gen.add_section(text)
            pe_gen.add_section(data)
            
            # Add required imports
            pe_gen.add_import("kernel32.dll", "ExitProcess")
            if len(self.string_literals) > 0:
                pe_gen.add_import("msvcrt.dll", "printf")
            
            # Generate PE file
            logging.info(f"Writing output file: {output_file}")
            pe_gen.generate(output_file, text_section, data_section)
            
            if output_file.exists():
                logging.info(f"Successfully generated executable: {output_file}")
                logging.info(f"File size: {output_file.stat().st_size} bytes")
                return True
            else:
                logging.error("Failed to create output file")
                return False
            
        except Exception as e:
            logging.error(f"Error generating Windows executable: {str(e)}", exc_info=True)
            return False
            
    def _generate_text_section(self, ir: Dict) -> bytes:
        """Generates machine code for .text section"""
        try:
            logging.info("Generating text section...")
            
            # Convert IR instructions to assembler format
            instructions = []
            
            # Add initialization code
            for instr in ir.get('init', []):
                if instr['type'] == 'label':
                    instructions.append({
                        'label': instr['name']
                    })
                elif instr['type'] == 'instruction':
                    if instr['opcode'].value == 'call' and 'target' in instr:
                        # External function call
                        instructions.append({
                            'opcode': 'call',
                            'target': instr['target']
                        })
                    else:
                        # Normal instruction
                        instructions.append({
                            'opcode': instr['opcode'].value,
                            'operands': [self._convert_operand(op) for op in instr.get('operands', [])]
                        })
            
            # Add function code
            for func in ir['functions'].values():
                for instr in func['instructions']:
                    if instr['type'] == 'label':
                        instructions.append({
                            'label': instr['name']
                        })
                    elif instr['type'] == 'instruction':
                        if instr['opcode'].value == 'call' and 'target' in instr:
                            # External function call
                            instructions.append({
                                'opcode': 'call',
                                'target': instr['target']
                            })
                        else:
                            # Normal instruction
                            instructions.append({
                                'opcode': instr['opcode'].value,
                                'operands': [self._convert_operand(op) for op in instr.get('operands', [])]
                            })
                        
            # Assemble code
            logging.info("Assembling instructions...")
            machine_code = self.assembler.assemble(instructions)
            logging.info(f"Generated {len(machine_code)} bytes of machine code")
            
            return machine_code
            
        except Exception as e:
            logging.error(f"Error generating text section: {str(e)}", exc_info=True)
            return b''
            
    def _generate_data_section(self, ir: Dict) -> bytes:
        """Generates data section with strings"""
        data = bytearray()
        
        # Add strings
        for label, string in ir.get('strings', {}).items():
            # Remove quotes
            string = string.strip('"')
            # Add null terminator
            data.extend(string.encode('utf-8') + b'\0')
            
        return bytes(data)
        
    def _convert_operand(self, op) -> Operand:
        """Converts IR operand to assembler operand"""
        if isinstance(op, str):
            # Register
            try:
                reg = Register[op.upper()]
                return Operand(OperandType.REGISTER, reg)
            except KeyError:
                # Label/symbol
                return Operand(OperandType.LABEL, op)
        elif isinstance(op, int):
            # Immediate
            return Operand(OperandType.IMMEDIATE, op)
        elif isinstance(op, dict):
            # Structured operand
            if op.get('type') == 'register':
                reg = Register[op['value'].upper()]
                return Operand(OperandType.REGISTER, reg)
            elif op.get('type') == 'memory':
                return Operand(OperandType.MEMORY, op['value'])
            elif op.get('type') == 'immediate':
                return Operand(OperandType.IMMEDIATE, op['value'])
        raise ValueError(f"Invalid operand: {op}")
            
    def supports_platform(self, platform: Platform) -> bool:
        return platform == Platform.WINDOWS
        
    def supports_architecture(self, arch: Architecture) -> bool:
        return arch in [Architecture.X86, Architecture.X64]
        
    def get_file_extension(self) -> str:
        return ".exe"