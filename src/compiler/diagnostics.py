# MetaForge Compiler - Diagnostics
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
# Module: Diagnostics
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Contiene le informazioni dei messaggi di errore e di warning del compilatore.
#
# Key Features:
# - fornisce un elenco di codici di errore e di warning
# - fornisce un elenco di livelli di errori e di warning
# - fornisce una funzione per creare nuovi messaggi di errore e di warning
#
# Usage & Extensibility:
# Questo modulo deve essere importato e utilizzato per creare messaggi di errore e di warning all'interno del compilatore.
# ---------------------------------------------------------------------------------
from pathlib import Path
import logging

class DiagnosticLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class DiagnosticCode(Enum):
    # Lexical errors
    INVALID_CHARACTER = "E001"
    UNTERMINATED_STRING = "E002"
    
    # Syntax errors
    UNEXPECTED_TOKEN = "E003"
    MISSING_TOKEN = "E004"
    
    # Type errors
    TYPE_MISMATCH = "E005"
    UNDEFINED_TYPE = "E006"
    INCOMPATIBLE_TYPES = "E007"
    
    # Name errors
    UNDEFINED_VARIABLE = "E008"
    UNDEFINED_FUNCTION = "E009"
    UNDEFINED_CLASS = "E010"
    UNDEFINED_MEMBER = "E011"
    
    # OOP errors
    ABSTRACT_INSTANTIATION = "E012"
    MISSING_OVERRIDE = "E013"
    INVALID_OVERRIDE = "E014"
    INTERFACE_VIOLATION = "E015"
    
    # Other errors
    COMPILATION_ERROR = "E999"
    TYPE_ERROR = "E998"

class DiagnosticEmitter:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def emit_error(self, message: str, file: Path, code: DiagnosticCode, line: int = 0, column: int = 0):
        """Emit an error diagnostic"""
        error = {
            'level': DiagnosticLevel.ERROR,
            'code': code,
            'message': message,
            'file': str(file),
            'line': line,
            'column': column
        }
        self.errors.append(error)
        logging.error(f"{file}:{line}:{column}: error {code.value}: {message}")
        
    def emit_warning(self, message: str, file: Path, code: DiagnosticCode, line: int = 0, column: int = 0):
        """Emit a warning diagnostic"""
        warning = {
            'level': DiagnosticLevel.WARNING,
            'code': code,
            'message': message,
            'file': str(file),
            'line': line,
            'column': column
        }
        self.warnings.append(warning)
        logging.warning(f"{file}:{line}:{column}: warning {code.value}: {message}")
        
    def emit_info(self, message: str, file: Path = None):
        """Emit an informational diagnostic"""
        if file:
            logging.info(f"{file}: {message}")
        else:
            logging.info(message)
            
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
        
    def get_error_count(self) -> int:
        """Get the number of errors"""
        return len(self.errors)
        
    def get_warning_count(self) -> int:
        """Get the number of warnings"""
        return len(self.warnings)
        
    def clear(self):
        """Clear all diagnostics"""
        self.errors.clear()
        self.warnings.clear()