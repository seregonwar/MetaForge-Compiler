from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict
from pathlib import Path
import json
import os

class DiagnosticLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info" 
    HINT = "hint"

class DiagnosticCode(Enum):
    # Syntax errors
    SYNTAX_ERROR = "E001"
    UNEXPECTED_TOKEN = "E002"
    MISSING_TOKEN = "E003"
    
    # Semantic errors
    TYPE_ERROR = "E101"
    UNDEFINED_SYMBOL = "E102"
    REDEFINED_SYMBOL = "E103"
    
    # Compilation errors
    COMPILATION_ERROR = "E201"
    LINKER_ERROR = "E202"
    
    # Warnings
    UNUSED_VARIABLE = "W001"
    IMPLICIT_CONVERSION = "W002"
    DEPRECATED_FEATURE = "W003"

@dataclass
class Diagnostic:
    level: DiagnosticLevel
    code: DiagnosticCode
    message: str
    location: 'SourceLocation'
    hint: Optional[str] = None
    related: List['Diagnostic'] = None

@dataclass 
class SourceLocation:
    file: Path
    line: int
    column: int

class DiagnosticEmitter:
    """Handles emission and formatting of diagnostics"""
    
    def __init__(self):
        self.diagnostics: List[Diagnostic] = []
        self.db = DiagnosticDB()
        
    def emit_error(self, message: str, file: Path, line: int = 1, column: int = 1, code: DiagnosticCode = DiagnosticCode.COMPILATION_ERROR):
        """Emits an error"""
        self.emit(Diagnostic(
            level=DiagnosticLevel.ERROR,
            code=code,
            message=message,
            location=SourceLocation(file, line, column)
        ))
        
    def emit_warning(self, message: str, file: Path, line: int = 1, column: int = 1, code: DiagnosticCode = DiagnosticCode.DEPRECATED_FEATURE):
        """Emits a warning"""
        self.emit(Diagnostic(
            level=DiagnosticLevel.WARNING,
            code=code,
            message=message,
            location=SourceLocation(file, line, column)
        ))
        
    def emit(self, diagnostic: Diagnostic):
        """Emits a diagnostic"""
        self.diagnostics.append(diagnostic)
        self._print_diagnostic(diagnostic)
        
    def _print_diagnostic(self, d: Diagnostic):
        """Formats and prints a diagnostic in modern style"""
        # ANSI colors
        colors = {
            DiagnosticLevel.ERROR: "\033[1;31m",   # Bold red
            DiagnosticLevel.WARNING: "\033[1;33m",  # Bold yellow
            DiagnosticLevel.INFO: "\033[1;36m",     # Bold cyan
            DiagnosticLevel.HINT: "\033[1;32m"      # Bold green
        }
        reset = "\033[0m"
        
        # Header
        print(f"\n{colors[d.level]}{d.level.value}[{d.code.value}]{reset}: {d.message}")
        
        # Location
        print(f"  --> {d.location.file}:{d.location.line}:{d.location.column}")
        
        # Code snippet
        if d.location.file.exists():
            self._print_code_snippet(d.location)
            
        # Hint
        if d.hint:
            print(f"{colors[DiagnosticLevel.HINT]}hint:{reset} {d.hint}")
            
        # Known solution
        solution = self.db.get_solution(d)
        if solution:
            print(f"\n{colors[DiagnosticLevel.INFO]}suggested fix:{reset} {solution}")
            
    def _print_code_snippet(self, location: SourceLocation):
        """Prints code snippet with error highlighting"""
        try:
            lines = location.file.read_text().splitlines()
            line_num = location.line - 1
            
            # Print 3 lines of context
            start = max(0, line_num - 2)
            end = min(len(lines), line_num + 3)
            
            print()
            for i in range(start, end):
                prefix = "  "
                if i == line_num:
                    prefix = "->"
                print(f"{prefix} {i+1:>4} | {lines[i]}")
                
                if i == line_num:
                    # Highlight error column
                    print(f"     | {' ' * (location.column-1)}^")
                    
        except Exception:
            pass

class DiagnosticDB:
    """Database of known errors and solutions"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / "diagnostic_db.json"
        self.known_issues = self._load_db()
        
    def _load_db(self) -> Dict:
        if not self.db_path.exists():
            return {}
        return json.loads(self.db_path.read_text())
        
    def get_solution(self, diagnostic: Diagnostic) -> Optional[str]:
        """Looks up known solution for diagnostic"""
        key = f"{diagnostic.code.value}:{diagnostic.message}"
        return self.known_issues.get(key)
        
    def add_solution(self, diagnostic: Diagnostic, solution: str):
        """Adds new solution to database"""
        key = f"{diagnostic.code.value}:{diagnostic.message}"
        self.known_issues[key] = solution
        
        with open(self.db_path, 'w') as f:
            json.dump(self.known_issues, f, indent=2)