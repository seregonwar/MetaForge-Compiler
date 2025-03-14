# MetaForge Compiler - Syntax Manager
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
# Module: Syntax Manager
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Manage syntax rules for different programming languages.
#
# Key Features:
# - Multi-language support
# - Customizable syntax rules
#
# Usage & Extensibility:
# This module can be used to parse and generate code in various languages.
# You can extend the module by adding new syntax rules or modifying existing ones.
#
# ---------------------------------------------------------------------------------
from typing import Dict, List, Optional
import logging
from .lexer import MetaForgeLexer
from .parser import MetaForgeParser

class SyntaxStyle(Enum):
    PYTHON = "python"
    C = "c"
    RUST = "rust"
    LISP = "lisp"
    CUSTOM = "custom"

class SyntaxRule:
    def __init__(self, style: SyntaxStyle, pattern: str, transform: str):
        self.style = style
        self.pattern = pattern  # Regex pattern to match
        self.transform = transform  # Transform to MetaForge IR
        
class MultiSyntaxManager:
    def __init__(self):
        self.current_style = SyntaxStyle.PYTHON
        self.rules: Dict[SyntaxStyle, List[SyntaxRule]] = {}
        self._init_rules()
        self.logger = logging.getLogger("MetaForge.SyntaxManager")
        
    def _init_rules(self):
        """Initialize syntax rules for different styles"""
        # Python-style rules
        python_rules = [
            SyntaxRule(
                SyntaxStyle.PYTHON,
                r"def\s+(\w+)\s*\((.*?)\)\s*->?\s*([\w\[\]]*)\s*:",
                "fn {1}({2}) -> {3} {"
            ),
            SyntaxRule(
                SyntaxStyle.PYTHON,
                r"class\s+(\w+)(?:\s*\((.*?)\))?\s*:",
                "class {1} extends {2} {"
            )
        ]
        self.rules[SyntaxStyle.PYTHON] = python_rules
        
        # C-style rules
        c_rules = [
            SyntaxRule(
                SyntaxStyle.C,
                r"([\w\*]+)\s+(\w+)\s*\((.*?)\)\s*{",
                "fn {2}({3}) -> {1} {"
            ),
            SyntaxRule(
                SyntaxStyle.C,
                r"struct\s+(\w+)\s*{",
                "class {1} {"
            )
        ]
        self.rules[SyntaxStyle.C] = c_rules
        
        # Rust-style rules
        rust_rules = [
            SyntaxRule(
                SyntaxStyle.RUST,
                r"fn\s+(\w+)\s*\((.*?)\)\s*->\s*([\w\[\]]*)\s*{",
                "fn {1}({2}) -> {3} {"
            ),
            SyntaxRule(
                SyntaxStyle.RUST,
                r"impl\s+(\w+)(?:\s+for\s+(\w+))?\s*{",
                "impl {1} for {2} {"
            )
        ]
        self.rules[SyntaxStyle.RUST] = rust_rules
        
        # Lisp-style rules
        lisp_rules = [
            SyntaxRule(
                SyntaxStyle.LISP,
                r"\(defun\s+(\w+)\s*\((.*?)\).*?\)",
                "fn {1}({2}) {"
            ),
            SyntaxRule(
                SyntaxStyle.LISP,
                r"\(defclass\s+(\w+)\s*\((.*?)\)",
                "class {1} extends {2} {"
            )
        ]
        self.rules[SyntaxStyle.LISP] = lisp_rules
        
    def detect_style(self, code: str) -> SyntaxStyle:
        """Detect the syntax style of the code"""
        # Count style-specific markers
        markers = {
            SyntaxStyle.PYTHON: len(code.split('def ')) + len(code.split('class ')),
            SyntaxStyle.C: code.count(';') + code.count('{}'),
            SyntaxStyle.RUST: len(code.split('fn ')) + len(code.split('impl ')),
            SyntaxStyle.LISP: code.count('(defun') + code.count('(defclass')
        }
        
        # Return style with most markers
        return max(markers.items(), key=lambda x: x[1])[0]
        
    def transform_to_ir(self, code: str, style: Optional[SyntaxStyle] = None) -> str:
        """Transform code from any supported syntax to MetaForge IR"""
        if style is None:
            style = self.detect_style(code)
            
        ir_code = code
        for rule in self.rules.get(style, []):
            # Apply transformation rules
            import re
            ir_code = re.sub(rule.pattern, rule.transform, ir_code)
            
        return ir_code
        
    def add_custom_rule(self, pattern: str, transform: str):
        """Add a custom syntax transformation rule"""
        if SyntaxStyle.CUSTOM not in self.rules:
            self.rules[SyntaxStyle.CUSTOM] = []
            
        rule = SyntaxRule(SyntaxStyle.CUSTOM, pattern, transform)
        self.rules[SyntaxStyle.CUSTOM].append(rule)
        
    def set_style(self, style: SyntaxStyle):
        """Set the current syntax style"""
        self.current_style = style
        
    def parse(self, source: str) -> Dict:
        """Parse source code into AST"""
        try:
            # Step 1: Lexical Analysis
            self.logger.debug("Starting lexical analysis")
            lexer = MetaForgeLexer(source)
            tokens = lexer.tokenize()
            self.logger.debug(f"Lexical analysis completed. Found {len(tokens)} tokens")
            
            # Log tokens for debugging
            for token in tokens[:10]:  # Show first 10 tokens
                self.logger.debug(f"Token: {token}")
                
            # Step 2: Parsing
            self.logger.debug("Starting parsing")
            parser = MetaForgeParser(tokens)
            ast = parser.parse()
            self.logger.debug("Parsing completed successfully")
            
            # Log AST for debugging
            self.logger.debug(f"AST root type: {ast.get('type', 'unknown')}")
            self.logger.debug(f"Number of declarations: {len(ast.get('declarations', []))}")
            
            return ast
            
        except Exception as e:
            self.logger.error(f"Failed to parse source code: {str(e)}")
            self.logger.error(f"Error occurred at line {getattr(e, 'line', 'unknown')}, column {getattr(e, 'column', 'unknown')}")
            raise
            
    def parse_file(self, filepath: str) -> Dict:
        """Parse a source file into AST"""
        try:
            with open(filepath, 'r') as f:
                source = f.read()
            return self.parse(source)
        except Exception as e:
            self.logger.error(f"Failed to parse file {filepath}: {str(e)}")
            raise
