import subprocess
from pathlib import Path
from typing import List, Dict
from ..utils.paths import VSPaths

class Compiler:
    def __init__(self):
        self.vs_paths = VSPaths()
        
        self.module_libs = {
            "core": ["ntdll.lib", "kernel32.lib", "advapi32.lib"],
            "crypto": ["ntdll.lib", "kernel32.lib", "advapi32.lib", "crypt32.lib"],
            "exploit": ["ntdll.lib", "kernel32.lib", "advapi32.lib", "shell32.lib", "user32.lib"]
        }

    def compile(self, 
                source_file: Path,
                output_file: Path,
                module: str,
                output_type: str = "dll") -> bool:
        """
        Compiles a C source file
        
        Args:
            source_file: C source file
            output_file: Output file
            module: Module name
            output_type: Output type ("dll" or "exe")
            
        Returns:
            True if compilation succeeds, False otherwise
        """
        try:
            compile_cmd = self._build_compile_command(
                source_file,
                output_file,
                module,
                output_type
            )
            
            # Create batch file
            batch_file = source_file.parent / "compile.bat"
            with open(batch_file, "w") as f:
                f.write(f'@echo off\n')
                f.write(f'call "{self.vs_paths.get_vcvars_path()}"\n')
                f.write(" ".join(compile_cmd))
            
            # Run compilation
            subprocess.run([str(batch_file)], check=True)
            return True
            
        except Exception as e:
            print(f"Compilation error {source_file}: {str(e)}")
            return False

    def _build_compile_command(self,
                             source: Path,
                             output: Path, 
                             module: str,
                             output_type: str) -> List[str]:
        """Builds the compilation command"""
        
        cmd = ["cl.exe"]
        
        # Output options
        if output_type == "dll":
            cmd.append("/LD")
        
        cmd.extend([
            "/MD",
            f"/Fe:{str(output)}",
            "/O2",
            "/GS-",
            "/D", "WIN32",
            "/D", "_WINDOWS", 
            "/D", "NDEBUG",
            "/D", "_UNICODE",
            "/D", "UNICODE"
        ])
        
        # Include paths
        for inc in self.vs_paths.include_paths:
            cmd.append(f"/I\"{inc}\"")
            
        # Source file
        cmd.append(str(source))
        
        # Linker options
        cmd.extend([
            "/link",
            "/NODEFAULTLIB:libcmt.lib"
        ])
        
        # Lib paths
        for lib in self.vs_paths.lib_paths:
            cmd.append(f"/LIBPATH:\"{lib}\"")
            
        # Module libs
        cmd.extend(self.module_libs[module])
        
        # Runtime libs
        cmd.extend([
            "ucrt.lib",
            "vcruntime.lib", 
            "msvcrt.lib"
        ])
        
        return cmd 