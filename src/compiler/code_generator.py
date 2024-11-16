from pathlib import Path
from typing import Dict, Optional
from .parser import MetaForgeLexer, MetaForgeParser
from .templates import get_template

class CodeGenerator:
    def __init__(self):
        pass

    def generate_code(self, 
                     mf_file: Path, 
                     output_dir: Path,
                     output_type: str = "dll") -> Optional[Path]:
        """
        Generates C code from MetaForge file
        
        Args:
            mf_file: Input MetaForge file
            output_dir: Output directory
            output_type: Output type ("dll" or "exe")
            
        Returns:
            Path of generated C file or None if error
        """
        try:
            # Read source file
            source = mf_file.read_text(encoding='utf-8')
            
            # Tokenize
            lexer = MetaForgeLexer(source)
            tokens = lexer.tokenize()
            
            # Parse
            parser = MetaForgeParser(tokens)
            ast = parser.parse()
            
            # Generate C code
            c_code = self._generate_c_code(ast, output_type)
            
            # Write output file
            output_file = output_dir / f"{mf_file.stem}.c"
            output_file.write_text(c_code)
            
            return output_file
            
        except Exception as e:
            print(f"Error generating code for {mf_file}: {str(e)}")
            return None
            
    def _generate_c_code(self, ast: Dict, output_type: str) -> str:
        """Generates C code from AST"""
        
        # Get base template
        template = get_template(output_type)
        
        # Separate imports from other declarations
        imports = []
        declarations = []
        
        for decl in ast['declarations']:
            try:
                if decl['type'] == 'Import':
                    imports.append(self._generate_import(decl))
                else:
                    declarations.append(self._generate_declaration(decl))
            except Exception as e:
                print(f"Warning: unable to generate declaration: {str(e)}")
                continue
                
        # Insert everything into template
        return template.format(
            forward_declarations='\n'.join(imports),
            declarations='\n'.join(declarations),
            globals='',  # Empty for now
            dll_init='',  # DLL only
            dll_cleanup=''  # DLL only
        )
        
    def _generate_declaration(self, node: Dict) -> str:
        """Generates C code for a declaration"""
        if node['type'] == 'Function':
            return self._generate_function(node)
        elif node['type'] == 'Struct':
            return self._generate_struct(node)
        elif node['type'] == 'Import':
            return self._generate_import(node)
        else:
            raise ValueError(f"Unsupported declaration type: {node['type']}")

    def _generate_function(self, node: Dict) -> str:
        """Generates C code for a function"""
        # If main function, use int as return type
        if node['name'] == 'main':
            return_type = 'int'
        else:
            return_type = self._convert_type(node['return_type'])
            
        # If main function, don't export it
        export_spec = "" if node['name'] == 'main' else "__declspec(dllexport) "
        
        # Generate parameters
        params = self._generate_parameters(node.get('params', []))
        
        # Generate body
        body = self._generate_statements(node.get('body', {'statements': []}))
        
        # Add indentation to body
        indented_body = '\n    '.join(line for line in body.split('\n'))
        
        return f"""
{export_spec}{return_type} {node['name']}({params}) {{
    {indented_body}
}}"""

    def _convert_type(self, mf_type: str) -> str:
        """Converts a MetaForge type to corresponding C type"""
        type_map = {
            'i8': 'int8_t',
            'i16': 'int16_t', 
            'i32': 'int32_t',
            'i64': 'int64_t',
            'u8': 'uint8_t',
            'u16': 'uint16_t',
            'u32': 'uint32_t',
            'u64': 'uint64_t',
            'f32': 'float',
            'f64': 'double',
            'bool': 'int',
            'void': 'void'
        }
        return type_map.get(mf_type, mf_type)

    def _generate_statements(self, node: Dict) -> str:
        """Generates C code for a list of statements"""
        statements = []
        for stmt in node.get('statements', []):
            if stmt['type'] == 'FunctionCall':
                statements.append(self._generate_function_call(stmt))
            elif stmt['type'] == 'Return':
                statements.append(self._generate_return(stmt))
                
        return '\n'.join(statements)
        
    def _generate_function_call(self, node: Dict) -> str:
        """Generates C code for a function call"""
        args = []
        for arg in node['arguments']:
            if arg['type'] == 'StringLiteral':
                args.append(arg['value'])  # Strings are already quoted
            elif arg['type'] == 'NumberLiteral':
                args.append(str(arg['value']))
                
        return f"{node['name']}({', '.join(args)});"
        
    def _generate_return(self, node: Dict) -> str:
        """Generates C code for a return statement"""
        if node['value']['type'] == 'NumberLiteral':
            return f"return {node['value']['value']};"
        # ... other value types ...

    def _generate_import(self, node: Dict) -> str:
        """Generates C code for an import"""
        if node['import_type'] == 'c':
            return f'#include <{node["path"]}>'
        elif node['import_type'] == 'cpp':
            return f'#include <{node["path"]}>'
        else:
            raise ValueError(f"Unsupported import type: {node['import_type']}")