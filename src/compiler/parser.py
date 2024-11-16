from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
import re
import logging

class TokenType(Enum):
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER" 
    STRING = "STRING"
    KEYWORD = "KEYWORD"
    OPERATOR = "OPERATOR"
    PUNCTUATION = "PUNCTUATION"
    TYPE = "TYPE"
    EOF = "EOF"

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
    
    def __str__(self):
        return f"{self.type.value}({self.value}) at line {self.line}, col {self.column}"

class MetaForgeLexer:
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        
        self.keywords = {
            'fn', 'struct', 'enum', 'let', 'if', 'else', 'while', 'for',
            'ret', 'alloc', 'free', 'deref', 'ref', 'try', 'catch',
            'match', 'import', 'encrypt', 'decrypt', 'hash', 'genkey', 'cipher'
        }
        
        self.types = {
            'i8', 'i16', 'i32', 'i64', 'u8', 'u16', 'u32', 'u64',
            'f32', 'f64', 'bool', 'ptr', 'key', 'cipher', 'hash',
            'bytes', 'stream'
        }
        
        logging.debug(f"Initializing lexer with source:\n{source}")
        
    def tokenize(self) -> List[Token]:
        tokens = []
        
        while self.pos < len(self.source):
            logging.debug(f"Lexing at position {self.pos} (line {self.line}, col {self.column})")
            
            # Skip whitespace
            if self.source[self.pos].isspace():
                if self.source[self.pos] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue

            # Comments
            if self.pos + 1 < len(self.source) and self.source[self.pos:self.pos+2] == '//':
                logging.debug(f"Found comment at line {self.line}")
                while self.pos < len(self.source) and self.source[self.pos] != '\n':
                    self.pos += 1
                continue

            # Identifiers and keywords
            if self.source[self.pos].isalpha() or self.source[self.pos] == '_':
                start = self.pos
                start_column = self.column
                
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
                    self.pos += 1
                    self.column += 1
                    
                value = self.source[start:self.pos]
                
                if value in self.keywords:
                    token = Token(TokenType.KEYWORD, value, self.line, start_column)
                    logging.debug(f"Found keyword: {token}")
                elif value in self.types:
                    token = Token(TokenType.TYPE, value, self.line, start_column)
                    logging.debug(f"Found type: {token}")
                else:
                    token = Token(TokenType.IDENTIFIER, value, self.line, start_column)
                    logging.debug(f"Found identifier: {token}")
                    
                tokens.append(token)
                continue

            # Numbers
            if self.source[self.pos].isdigit():
                start = self.pos
                start_column = self.column
                
                while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
                    self.pos += 1
                    self.column += 1
                    
                token = Token(TokenType.NUMBER, self.source[start:self.pos], self.line, start_column)
                logging.debug(f"Found number: {token}")
                tokens.append(token)
                continue

            # Strings
            if self.source[self.pos] == '"':
                start = self.pos
                start_column = self.column
                self.pos += 1
                self.column += 1
                
                while self.pos < len(self.source) and self.source[self.pos] != '"':
                    if self.source[self.pos] == '\\':
                        self.pos += 2
                        self.column += 2
                    else:
                        self.pos += 1
                        self.column += 1
                        
                if self.pos < len(self.source):  # Include closing quote
                    self.pos += 1
                    self.column += 1
                    
                token = Token(TokenType.STRING, self.source[start:self.pos], self.line, start_column)
                logging.debug(f"Found string: {token}")
                tokens.append(token)
                continue

            # Operators and punctuation
            if self.source[self.pos] in '+-*/%=<>!&|^~.':
                start = self.pos
                start_column = self.column
                
                while self.pos < len(self.source) and self.source[self.pos] in '+-*/%=<>!&|^~.':
                    self.pos += 1
                    self.column += 1
                    
                token = Token(TokenType.OPERATOR, self.source[start:self.pos], self.line, start_column)
                logging.debug(f"Found operator: {token}")
                tokens.append(token)
                continue

            # Single character punctuation
            token = Token(TokenType.PUNCTUATION, self.source[self.pos], self.line, self.column)
            logging.debug(f"Found punctuation: {token}")
            tokens.append(token)
            self.pos += 1
            self.column += 1

        # Add EOF token
        token = Token(TokenType.EOF, "", self.line, self.column)
        logging.debug(f"Adding EOF token: {token}")
        tokens.append(token)
        
        logging.info(f"Lexical analysis completed. Found {len(tokens)} tokens")
        return tokens

class MetaForgeParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = None
        self.next()
        
    def next(self):
        """Advance to next token"""
        if self.pos < len(self.tokens):
            self.current_token = self.tokens[self.pos]
            self.pos += 1
        else:
            self.current_token = Token(TokenType.EOF, "", 0, 0)
            
    def peek(self) -> Token:
        """Look at next token without consuming it"""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, "", 0, 0)
        
    def parse(self) -> Dict:
        """Parse MetaForge source code and return AST"""
        program = {
            'type': 'Program',
            'declarations': []
        }
        
        while self.current_token.type != TokenType.EOF:
            try:
                decl = self._parse_top_level()
                if decl:
                    program['declarations'].append(decl)
            except Exception as e:
                self._error(f"Parsing error: {str(e)}")
                # Try to recover from error by advancing to next statement
                self._sync()
                
        return program
        
    def _sync(self):
        """Recover from error by advancing to next valid statement"""
        while self.current_token.type != TokenType.EOF:
            if self.current_token.type == TokenType.PUNCTUATION and self.current_token.value == ';':
                self.next()
                return
            if self.current_token.type == TokenType.KEYWORD and self.current_token.value in {'fn', 'struct', 'enum', 'import'}:
                return
            self.next()
        
    def _parse_top_level(self) -> Optional[Dict]:
        """Parse top-level declarations"""
        if self.current_token.type == TokenType.KEYWORD:
            if self.current_token.value == 'import':
                return self._parse_import()
            elif self.current_token.value == 'fn':
                return self._parse_function()
            elif self.current_token.value == 'struct':
                return self._parse_struct()
            elif self.current_token.value == 'enum':
                return self._parse_enum()
                
        self._error(f"Unexpected token {self.current_token.type} at top level")
        return None
        
    def _parse_import(self) -> Dict:
        """Parse import statement"""
        # Consume 'import'
        self._expect(TokenType.KEYWORD, 'import')
        
        # Import type
        import_type = self._expect(TokenType.STRING)
        
        # Path
        path = self._expect(TokenType.STRING)
        
        # Semicolon
        self._expect(TokenType.PUNCTUATION, ';')
        
        return {
            'type': 'Import',
            'import_type': import_type.value.strip('"'),
            'path': path.value.strip('"')
        }
        
    def _parse_function(self) -> Dict:
        """Parse function declaration"""
        # Consume 'fn'
        self._expect(TokenType.KEYWORD, 'fn')
        
        # Function name
        name = self._expect(TokenType.IDENTIFIER)
        
        # Parameters
        self._expect(TokenType.PUNCTUATION, '(')
        params = self._parse_parameter_list()
        self._expect(TokenType.PUNCTUATION, ')')
        
        # Return type
        self._expect(TokenType.OPERATOR, '->')
        return_type = self._expect(TokenType.TYPE)
        
        # Function body
        body = self._parse_block()
        
        return {
            'type': 'Function',
            'name': name.value,
            'params': params,
            'return_type': return_type.value,
            'body': body
        }
        
    def _parse_block(self) -> Dict:
        """Parse code block"""
        self._expect(TokenType.PUNCTUATION, '{')
        
        statements = []
        while self.current_token.type != TokenType.PUNCTUATION or self.current_token.value != '}':
            stmt = self._parse_statement()
            if stmt:
                statements.append(stmt)
                
        self._expect(TokenType.PUNCTUATION, '}')
        
        return {
            'type': 'Block',
            'statements': statements
        }
        
    def _parse_statement(self) -> Optional[Dict]:
        """Parse statement"""
        if self.current_token.type == TokenType.IDENTIFIER:
            return self._parse_function_call()
        elif self.current_token.type == TokenType.KEYWORD and self.current_token.value == 'ret':
            return self._parse_return()
            
        self._error(f"Unexpected token in statement: {self.current_token.type}")
        return None
        
    def _parse_function_call(self) -> Dict:
        """Parse function call"""
        name = self._expect(TokenType.IDENTIFIER)
        
        self._expect(TokenType.PUNCTUATION, '(')
        args = []
        
        while self.current_token.type != TokenType.PUNCTUATION or self.current_token.value != ')':
            arg = self._parse_expression()
            args.append(arg)
            
            if self.current_token.value == ',':
                self.next()
                
        self._expect(TokenType.PUNCTUATION, ')')
        self._expect(TokenType.PUNCTUATION, ';')
        
        return {
            'type': 'FunctionCall',
            'name': name.value,
            'arguments': args
        }
        
    def _parse_return(self) -> Dict:
        """Parse return statement"""
        self._expect(TokenType.KEYWORD, 'ret')
        value = self._parse_expression()
        self._expect(TokenType.PUNCTUATION, ';')
        
        return {
            'type': 'Return',
            'value': value
        }
        
    def _parse_expression(self) -> Dict:
        """Parse expression"""
        if self.current_token.type == TokenType.STRING:
            value = self.current_token.value
            self.next()
            return {
                'type': 'StringLiteral',
                'value': value
            }
        elif self.current_token.type == TokenType.NUMBER:
            value = int(self.current_token.value)
            self.next()
            return {
                'type': 'NumberLiteral',
                'value': value
            }
            
        self._error(f"Unexpected token in expression: {self.current_token.type}")
        return None
        
    def _expect(self, type: TokenType, value: str = None) -> Token:
        """Verify and consume expected token"""
        if self.current_token.type != type:
            self._error(f"Expected {type}, got {self.current_token.type}")
            
        if value is not None and self.current_token.value != value:
            self._error(f"Expected '{value}', got '{self.current_token.value}'")
            
        token = self.current_token
        self.next()
        return token
        
    def _error(self, message: str):
        """Generate parsing error"""
        raise SyntaxError(f"{message} at line {self.current_token.line}, column {self.current_token.column}")
        
    def _parse_parameter_list(self) -> List[Dict]:
        """Parse function parameter list"""
        params = []
        
        # If next token is ')', list is empty
        if self.current_token.type == TokenType.PUNCTUATION and self.current_token.value == ')':
            return params
            
        # Otherwise parse parameters
        while True:
            param = self._parse_parameter()
            params.append(param)
            
            # If next token is ')', end of list
            if self.current_token.type == TokenType.PUNCTUATION and self.current_token.value == ')':
                break
                
            # Otherwise must be a comma
            if self.current_token.type != TokenType.PUNCTUATION or self.current_token.value != ',':
                self._error("Expected ',' or ')' in parameter list")
                
            self.next()  # Consume comma
            
        return params
        
    def _parse_parameter(self) -> Dict:
        """Parse single function parameter"""
        # Parameter type
        param_type = self._expect(TokenType.TYPE)
        
        # Parameter name
        param_name = self._expect(TokenType.IDENTIFIER)
        
        return {
            'type': 'Parameter',
            'param_type': param_type.value,
            'name': param_name.value
        }