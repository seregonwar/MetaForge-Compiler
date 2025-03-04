from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import logging

class TokenType(Enum):
    # Keywords
    FUNC = 'func'
    FN = 'fn'
    IF = 'if'
    ELSE = 'else'
    WHILE = 'while'
    FOR = 'for'
    IN = 'in'
    RETURN = 'return'
    BREAK = 'break'
    CONTINUE = 'continue'
    CLASS = 'class'
    EXTENDS = 'extends'
    IMPLEMENTS = 'implements'
    INTERFACE = 'interface'
    PUBLIC = 'public'
    PRIVATE = 'private'
    PROTECTED = 'protected'
    STATIC = 'static'
    FINAL = 'final'
    ABSTRACT = 'abstract'
    ASYNC = 'async'
    AWAIT = 'await'
    SPAWN = 'spawn'
    AUTO = 'auto'
    CONST = 'const'
    LET = 'let'
    VAR = 'var'
    RANGE = 'range'
    IMPORT = 'import'
    RET = 'ret'
    TYPE = 'type'
    HYBRID = 'hybrid'
    
    # Literals
    INTEGER = 'INTEGER'
    FLOAT = 'FLOAT'
    STRING = 'STRING'
    BOOL = 'BOOL'
    NULL = 'NULL'
    IDENTIFIER = 'IDENTIFIER'
    
    # Operators
    PLUS = '+'
    MINUS = '-'
    MULTIPLY = '*'
    DIVIDE = '/'
    MODULO = '%'
    POWER = '**'
    
    # Comparison
    EQUALS = '=='
    NOT_EQUALS = '!='
    LESS_THAN = '<'
    GREATER_THAN = '>'
    LESS_EQUALS = '<='
    GREATER_EQUALS = '>='
    
    # Assignment
    ASSIGN = '='
    PLUS_ASSIGN = '+='
    MINUS_ASSIGN = '-='
    MULTIPLY_ASSIGN = '*='
    DIVIDE_ASSIGN = '/='
    MODULO_ASSIGN = '%='
    
    # Logical
    AND = '&&'
    OR = '||'
    NOT = '!'
    
    # Bitwise
    BIT_AND = '&'
    BIT_OR = '|'
    BIT_XOR = '^'
    BIT_NOT = '~'
    LEFT_SHIFT = '<<'
    RIGHT_SHIFT = '>>'
    
    # Delimiters
    LEFT_PAREN = '('
    RIGHT_PAREN = ')'
    LEFT_BRACE = '{'
    RIGHT_BRACE = '}'
    LEFT_BRACKET = '['
    RIGHT_BRACKET = ']'
    COMMA = ','
    DOT = '.'
    COLON = ':'
    SEMICOLON = ';'
    AT = '@'
    ARROW = '->'
    LESS = '<'
    GREATER = '>'
    
    # Special
    EOF = 'EOF'
    COMMENT = 'COMMENT'
    WHITESPACE = 'WHITESPACE'
    NEWLINE = 'NEWLINE'
    GENERIC_LESS_THAN = '<'
    GENERIC_GREATER_THAN = '>'
    GENERIC_COMMA = ','
    GENERIC_LEFT_BRACKET = '['
    GENERIC_RIGHT_BRACKET = ']'
    
    def __str__(self):
        return self.value

KEYWORDS = {
    'func': TokenType.FUNC,
    'fn': TokenType.FN,
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'while': TokenType.WHILE,
    'for': TokenType.FOR,
    'in': TokenType.IN,
    'return': TokenType.RETURN,
    'break': TokenType.BREAK,
    'continue': TokenType.CONTINUE,
    'class': TokenType.CLASS,
    'extends': TokenType.EXTENDS,
    'implements': TokenType.IMPLEMENTS,
    'interface': TokenType.INTERFACE,
    'public': TokenType.PUBLIC,
    'private': TokenType.PRIVATE,
    'protected': TokenType.PROTECTED,
    'static': TokenType.STATIC,
    'final': TokenType.FINAL,
    'abstract': TokenType.ABSTRACT,
    'async': TokenType.ASYNC,
    'await': TokenType.AWAIT,
    'spawn': TokenType.SPAWN,
    'auto': TokenType.AUTO,
    'const': TokenType.CONST,
    'let': TokenType.LET,
    'var': TokenType.VAR,
    'range': TokenType.RANGE,
    'import': TokenType.IMPORT,
    'ret': TokenType.RET,
    'hybrid': TokenType.HYBRID,
    'i32': TokenType.TYPE,
    'i64': TokenType.TYPE,
    'f32': TokenType.TYPE,
    'f64': TokenType.TYPE,
    'bool': TokenType.TYPE,
    'string': TokenType.TYPE,
    'void': TokenType.TYPE
}

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
        self.tokens = []
        
    def tokenize(self) -> List[Token]:
        """Convert source code into a list of tokens"""
        while self.pos < len(self.source):
            # Skip whitespace
            if self.source[self.pos].isspace():
                if self.source[self.pos] == '\n':
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue
                
            # Handle comments
            if self.source[self.pos] == '/':
                if self.pos + 1 < len(self.source):
                    if self.source[self.pos + 1] == '/':  # Single-line comment
                        start = self.pos
                        start_column = self.column
                        while self.pos < len(self.source) and self.source[self.pos] != '\n':
                            self.pos += 1
                            self.column += 1
                        token = Token(TokenType.COMMENT, self.source[start:self.pos], self.line, start_column)
                        logging.debug(f"Found comment: {token}")
                        self.tokens.append(token)
                        continue
                    elif self.source[self.pos + 1] == '*':  # Multi-line comment
                        start = self.pos
                        start_column = self.column
                        self.pos += 2
                        self.column += 2
                        while self.pos < len(self.source) - 1:
                            if self.source[self.pos] == '*' and self.source[self.pos + 1] == '/':
                                self.pos += 2
                                self.column += 2
                                break
                            if self.source[self.pos] == '\n':
                                self.line += 1
                                self.column = 1
                            else:
                                self.column += 1
                            self.pos += 1
                        token = Token(TokenType.COMMENT, self.source[start:self.pos], self.line, start_column)
                        logging.debug(f"Found comment: {token}")
                        self.tokens.append(token)
                        continue
                        
            # Numbers
            if self.source[self.pos].isdigit():
                start = self.pos
                start_column = self.column
                while self.pos < len(self.source) and (self.source[self.pos].isdigit() or self.source[self.pos] == '.'):
                    self.pos += 1
                    self.column += 1
                if '.' in self.source[start:self.pos]:
                    token = Token(TokenType.FLOAT, float(self.source[start:self.pos]), self.line, start_column)
                else:
                    token = Token(TokenType.INTEGER, int(self.source[start:self.pos]), self.line, start_column)
                logging.debug(f"Found number: {token}")
                self.tokens.append(token)
                continue
                
            # Strings
            if self.source[self.pos] in ['"', "'"]:
                quote = self.source[self.pos]
                start = self.pos
                start_column = self.column
                self.pos += 1
                self.column += 1
                while self.pos < len(self.source) and self.source[self.pos] != quote:
                    if self.source[self.pos] == '\\':
                        self.pos += 2
                        self.column += 2
                    else:
                        self.pos += 1
                        self.column += 1
                if self.pos < len(self.source):
                    self.pos += 1
                    self.column += 1
                token = Token(TokenType.STRING, self.source[start:self.pos], self.line, start_column)
                logging.debug(f"Found string: {token}")
                self.tokens.append(token)
                continue
                
            # Identifiers and keywords
            if self.source[self.pos].isalpha() or self.source[self.pos] == '_':
                start = self.pos
                start_column = self.column
                while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == '_'):
                    self.pos += 1
                    self.column += 1
                    
                value = self.source[start:self.pos]
                token_type = KEYWORDS.get(value.lower(), TokenType.IDENTIFIER)
                token = Token(token_type, value, self.line, start_column)
                logging.debug(f"Found identifier/keyword: {token}")
                self.tokens.append(token)
                continue
                
            # Two-character operators
            if self.pos + 1 < len(self.source):
                double_char = self.source[self.pos:self.pos + 2]
                if double_char == '->':
                    token = Token(TokenType.ARROW, double_char, self.line, self.column)
                    self.pos += 2
                    self.column += 2
                    self.tokens.append(token)
                    continue
                    
            # Single-character operators and punctuation
            char = self.source[self.pos]
            if char in '+-*/%=<>!&|^~()[]{},.:;@':
                token = None
                if char == '(':
                    token = Token(TokenType.LEFT_PAREN, char, self.line, self.column)
                elif char == ')':
                    token = Token(TokenType.RIGHT_PAREN, char, self.line, self.column)
                elif char == '{':
                    token = Token(TokenType.LEFT_BRACE, char, self.line, self.column)
                elif char == '}':
                    token = Token(TokenType.RIGHT_BRACE, char, self.line, self.column)
                elif char == '[':
                    token = Token(TokenType.LEFT_BRACKET, char, self.line, self.column)
                elif char == ']':
                    token = Token(TokenType.RIGHT_BRACKET, char, self.line, self.column)
                elif char == ',':
                    token = Token(TokenType.COMMA, char, self.line, self.column)
                elif char == '.':
                    token = Token(TokenType.DOT, char, self.line, self.column)
                elif char == ':':
                    token = Token(TokenType.COLON, char, self.line, self.column)
                elif char == ';':
                    token = Token(TokenType.SEMICOLON, char, self.line, self.column)
                elif char == '@':
                    token = Token(TokenType.AT, char, self.line, self.column)
                elif char == '<':
                    token = Token(TokenType.GENERIC_LESS_THAN, char, self.line, self.column)
                elif char == '>':
                    token = Token(TokenType.GENERIC_GREATER_THAN, char, self.line, self.column)
                    
                if token:
                    logging.debug(f"Found operator: {token}")
                    self.tokens.append(token)
                    self.pos += 1
                    self.column += 1
                    continue
                    
            # Skip unknown characters
            logging.error(f"Unexpected character '{self.source[self.pos]}' at line {self.line}, column {self.column}")
            self.pos += 1
            self.column += 1
            
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        return self.tokens
