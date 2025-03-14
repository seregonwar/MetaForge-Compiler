# MetaForge Compiler - Parser
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
# Module: Parser
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Parsers the source code into an Abstract Syntax Tree.
#
# Key Features:
# - Recursive Descent Parsing
#
# Usage & Extensibility:
# The parser can be extended with new productions and rules.
from typing import List, Optional, Dict
from enum import Enum
import re
import logging
from .lexer import TokenType, Token

class MetaForgeParser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current_token = None
        self.logger = logging.getLogger("MetaForge.Parser")
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
        
    def expect(self, token_type: TokenType):
        """Expect current token to be of given type"""
        if self.current_token.type != token_type:
            raise SyntaxError(f"Expected {token_type.value}, got {self.current_token.type.value} at line {self.current_token.line}, column {self.current_token.column}")
        self.next()
        
    def parse(self) -> Dict:
        """Parse MetaForge source code and return AST"""
        program = {
            'type': 'Program',
            'declarations': []
        }
        
        while self.current_token.type != TokenType.EOF:
            # Skip comments
            self.skip_comments()
            
            # Check for decorators
            decorators = []
            while self.current_token.type == TokenType.AT:
                decorators.append(self.parse_decorator())
                
            if self.current_token.type == TokenType.IMPORT:
                decl = self.parse_import()
                decl['decorators'] = decorators
                program['declarations'].append(decl)
            elif self.current_token.type == TokenType.CLASS:
                decl = self.parse_class_declaration()
                decl['decorators'] = decorators
                program['declarations'].append(decl)
            elif self.current_token.type == TokenType.INTERFACE:
                decl = self.parse_interface_declaration()
                decl['decorators'] = decorators
                program['declarations'].append(decl)
            elif self.current_token.type in [TokenType.FN, TokenType.FUNC]:
                decl = self.parse_function_declaration()
                decl['decorators'] = decorators
                program['declarations'].append(decl)
            else:
                raise SyntaxError(f"Unexpected token {self.current_token.type.value} at line {self.current_token.line}, column {self.current_token.column}")
                
        return program
        
    def parse_decorator(self) -> Dict:
        """Parse a decorator"""
        # Skip any comments before @
        self.skip_comments()
        
        if self.current_token.type != TokenType.AT:
            raise SyntaxError(f"Expected '@', got {self.current_token.type.value}")
        self.next()  # Skip @
        
        # Skip any comments between @ and identifier
        self.skip_comments()
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected decorator name, got {self.current_token.type.value}")
        name = self.current_token.value
        self.next()
        
        # Skip any comments after identifier
        self.skip_comments()
        
        # Parse decorator arguments if present
        args = []
        if self.current_token.type == TokenType.LEFT_PAREN:
            self.next()  # Skip (
            
            # Skip any comments after (
            self.skip_comments()
            
            if self.current_token.type != TokenType.RIGHT_PAREN:
                while True:
                    # Skip any comments before argument
                    self.skip_comments()
                    
                    args.append(self.parse_expression())
                    
                    # Skip any comments after argument
                    self.skip_comments()
                    
                    if self.current_token.type == TokenType.RIGHT_PAREN:
                        break
                        
                    if self.current_token.type != TokenType.COMMA:
                        raise SyntaxError(f"Expected ',' or ')', got {self.current_token.type.value}")
                    self.next()  # Skip ,
                    
            self.next()  # Skip )
            
        return {
            'type': 'Decorator',
            'name': name,
            'arguments': args
        }
        
    def skip_comments(self):
        """Helper method to skip comments"""
        while self.current_token.type == TokenType.COMMENT:
            self.next()
            
    def parse_block(self) -> Dict:
        """Parse a block of statements"""
        # Skip any comments before {
        self.skip_comments()
        
        if self.current_token.type != TokenType.LEFT_BRACE:
            raise SyntaxError(f"Expected '{{', got {self.current_token.type.value}")
        self.next()  # Skip {
        
        statements = []
        while self.current_token.type != TokenType.RIGHT_BRACE:
            if self.current_token.type == TokenType.EOF:
                raise SyntaxError("Unexpected end of file while parsing block")
                
            # Skip comments
            self.skip_comments()
            
            # Handle empty statements
            if self.current_token.type == TokenType.SEMICOLON:
                self.next()
                continue
                
            # Parse the statement
            stmt = self.parse_statement()
            if stmt is not None:  # Skip None statements (like standalone comments)
                statements.append(stmt)
                
            # Optional semicolon after statement
            if self.current_token.type == TokenType.SEMICOLON:
                self.next()
                
        self.next()  # Skip }
        
        return {
            'type': 'Block',
            'statements': statements
        }
        
    def parse_function_declaration(self) -> Dict:
        """Parse a function declaration"""
        # Skip any comments before decorators
        self.skip_comments()
            
        # Check for decorators
        decorators = []
        while self.current_token.type == TokenType.AT:
            decorators.append(self.parse_decorator())
            # Skip any comments between decorators
            self.skip_comments()
            
        # Handle both 'func' and 'fn' keywords
        if self.current_token.type not in [TokenType.FN, TokenType.FUNC]:
            raise SyntaxError(f"Expected 'func' or 'fn', got {self.current_token.type.value}")
        self.next()
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected function name, got {self.current_token.type.value}")
        name = self.current_token.value
        self.next()
        
        # Parse generic parameters if present
        generic_params = []
        if self.current_token.type == TokenType.GENERIC_LESS_THAN:
            self.next()  # Skip <
            while True:
                # Skip any comments
                self.skip_comments()
                    
                if self.current_token.type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected type parameter name, got {self.current_token.type.value}")
                param_name = self.current_token.value
                self.next()
                
                # Skip any comments
                self.skip_comments()
                    
                # Parse optional type bounds
                bounds = []
                if self.current_token.type == TokenType.COLON:
                    self.next()  # Skip :
                    bounds.append(self.parse_type_expression())
                    
                    while self.current_token.type == TokenType.PLUS:
                        self.next()  # Skip +
                        bounds.append(self.parse_type_expression())
                        
                generic_params.append({
                    'type': 'GenericParameter',
                    'name': param_name,
                    'bounds': bounds
                })
                
                # Skip any comments
                self.skip_comments()
                
                if self.current_token.type == TokenType.GENERIC_GREATER_THAN:
                    self.next()  # Skip >
                    break
                elif self.current_token.type == TokenType.COMMA:
                    self.next()  # Skip ,
                else:
                    raise SyntaxError(f"Expected '>' or ',', got {self.current_token.type.value}")
                
        # Skip any comments
        self.skip_comments()
            
        if self.current_token.type != TokenType.LEFT_PAREN:
            raise SyntaxError(f"Expected '(', got {self.current_token.type.value}")
        self.next()  # Skip (
        
        # Parse parameters
        params = []
        if self.current_token.type != TokenType.RIGHT_PAREN:
            while True:
                # Skip any comments
                self.skip_comments()
                    
                if self.current_token.type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected parameter name, got {self.current_token.type.value}")
                param_name = self.current_token.value
                self.next()
                
                # Skip any comments
                self.skip_comments()
                    
                if self.current_token.type != TokenType.COLON:
                    raise SyntaxError(f"Expected ':', got {self.current_token.type.value}")
                self.next()  # Skip :
                
                # Skip any comments
                self.skip_comments()
                    
                param_type = self.parse_type_expression()
                
                params.append({
                    'name': param_name,
                    'type': param_type
                })
                
                # Skip any comments
                self.skip_comments()
                    
                if self.current_token.type == TokenType.RIGHT_PAREN:
                    break
                    
                if self.current_token.type != TokenType.COMMA:
                    raise SyntaxError(f"Expected ',' or ')', got {self.current_token.type.value}")
                self.next()  # Skip ,
                
        self.next()  # Skip )
        
        # Skip any comments
        self.skip_comments()
            
        # Parse return type if present
        return_type = None
        if self.current_token.type == TokenType.ARROW:
            self.next()  # Skip ->
            
            # Skip any comments
            self.skip_comments()
            
            return_type = self.parse_type_expression()
            
        # Skip any comments
        self.skip_comments()
            
        # Parse function body
        if self.current_token.type != TokenType.LEFT_BRACE:
            raise SyntaxError(f"Expected '{{', got {self.current_token.type.value}")
        self.next()  # Skip {
        
        body = []
        while self.current_token.type != TokenType.RIGHT_BRACE:
            if self.current_token.type == TokenType.EOF:
                raise SyntaxError("Unexpected end of file while parsing function body")
                
            # Skip comments
            self.skip_comments()
                
            # Handle empty statements
            if self.current_token.type == TokenType.SEMICOLON:
                self.next()
                continue
                
            # Parse the statement
            stmt = self.parse_statement()
            if stmt is not None:  # Skip None statements (like standalone comments)
                body.append(stmt)
                
            # Optional semicolon after statement
            if self.current_token.type == TokenType.SEMICOLON:
                self.next()
                
        self.next()  # Skip }
        
        return {
            'type': 'FunctionDeclaration',
            'name': name,
            'genericParams': generic_params,
            'params': params,
            'returnType': return_type,
            'body': {
                'type': 'Block',
                'statements': body
            },
            'decorators': decorators
        }
        
    def parse_type_expression(self) -> Dict:
        """Parse a type expression, which can be:
        1. A simple type (int, string, etc.)
        2. A generic type (List<T>, Map<K,V>, etc.)
        3. An array type (T[])
        4. A pointer type (T*)
        5. A hybrid type (hybrid T)
        """
        # Check for hybrid modifier
        is_hybrid = False
        if self.current_token.type == TokenType.HYBRID:
            is_hybrid = True
            self.next()
            
        # Parse base type (can be either an identifier or a built-in type)
        if self.current_token.type not in [TokenType.IDENTIFIER, TokenType.TYPE]:
            raise SyntaxError(f"Expected type name, got {self.current_token.type.value}")
            
        base_type = self.current_token.value
        self.next()  # Skip type name
        
        # Handle generic parameters
        generic_args = []
        if self.current_token.type == TokenType.GENERIC_LESS_THAN:
            self.next()  # Skip <
            while True:
                # Parse the type argument
                if self.current_token.type == TokenType.IDENTIFIER:
                    # Simple type parameter
                    generic_args.append({
                        'type': 'TypeExpression',
                        'baseType': self.current_token.value,
                        'isArray': False,
                        'arrayDimensions': 0,
                        'isPointer': False,
                        'genericArgs': [],
                        'isHybrid': False
                    })
                    self.next()
                else:
                    # Complex type expression
                    generic_args.append(self.parse_type_expression())
                    
                if self.current_token.type == TokenType.GENERIC_GREATER_THAN:
                    self.next()  # Skip >
                    break
                    
                if self.current_token.type != TokenType.COMMA:
                    raise SyntaxError(f"Expected ',' or '>', got {self.current_token.type.value}")
                self.next()  # Skip ,
                
        # Handle array type
        is_array = False
        array_dimensions = 0
        while self.current_token.type == TokenType.LEFT_BRACKET:
            is_array = True
            array_dimensions += 1
            self.next()  # Skip [
            
            # Skip array size if present
            if self.current_token.type == TokenType.INTEGER:
                self.next()
                
            if self.current_token.type != TokenType.RIGHT_BRACKET:
                raise SyntaxError(f"Expected ']', got {self.current_token.type.value}")
            self.next()  # Skip ]
            
        # Handle pointer type
        is_pointer = False
        if self.current_token.type == TokenType.MULTIPLY:
            is_pointer = True
            self.next()  # Skip *
            
        return {
            'type': 'TypeExpression',
            'baseType': base_type,
            'isArray': is_array,
            'arrayDimensions': array_dimensions,
            'isPointer': is_pointer,
            'genericArgs': generic_args,
            'isHybrid': is_hybrid
        }
        
    def parse_type(self) -> Dict:
        """Parse a type, which is a type expression with optional type bounds"""
        type_expr = self.parse_type_expression()
        
        # Parse type bounds if present
        bounds = []
        if self.current_token.type == TokenType.COLON:
            self.next()  # Skip :
            bounds.append(self.parse_type_expression())
            
            while self.current_token.type == TokenType.PLUS:
                self.next()  # Skip +
                bounds.append(self.parse_type_expression())
                
        type_expr['bounds'] = bounds
        return type_expr
        
    def parse_generic_parameters(self) -> List[Dict]:
        """Parse generic parameters in a type or function declaration"""
        generic_params = []
        
        if self.current_token.type == TokenType.GENERIC_LESS_THAN:
            self.next()  # Skip <
            while True:
                if self.current_token.type != TokenType.IDENTIFIER:
                    raise SyntaxError(f"Expected type parameter name, got {self.current_token.type.value}")
                
                param_name = self.current_token.value
                self.next()
                
                # Parse optional type bounds
                bounds = []
                if self.current_token.type == TokenType.COLON:
                    self.next()  # Skip :
                    bounds.append(self.parse_type())
                    
                    while self.current_token.type == TokenType.PLUS:
                        self.next()  # Skip +
                        bounds.append(self.parse_type())
                        
                generic_params.append({
                    'type': 'GenericParameter',
                    'name': param_name,
                    'bounds': bounds
                })
                
                if self.current_token.type == TokenType.GENERIC_GREATER_THAN:
                    self.next()  # Skip >
                    break
                    
                if self.current_token.type != TokenType.COMMA:
                    raise SyntaxError(f"Expected ',' or '>', got {self.current_token.type.value}")
                self.next()  # Skip ,
                
        return generic_params
        
    def parse_statement(self) -> Optional[Dict]:
        """Parse a statement"""
        # Skip comments
        self.skip_comments()
        
        # Handle decorators at statement level
        decorators = []
        while self.current_token.type == TokenType.AT:
            decorators.append(self.parse_decorator())
            
        # Function declarations
        if self.current_token.type in [TokenType.FN, TokenType.FUNC]:
            decl = self.parse_function_declaration()
            decl['decorators'].extend(decorators)
            return decl
            
        # Class declarations
        if self.current_token.type == TokenType.CLASS:
            decl = self.parse_class_declaration()
            decl['decorators'].extend(decorators)
            return decl
            
        # Variable declarations
        if self.current_token.type in [TokenType.LET, TokenType.AUTO]:
            return self.parse_variable_declaration()
            
        # Control flow statements
        if self.current_token.type == TokenType.IF:
            return self.parse_if_statement()
        if self.current_token.type == TokenType.WHILE:
            return self.parse_while_statement()
        if self.current_token.type == TokenType.FOR:
            return self.parse_for_statement()
        if self.current_token.type == TokenType.RET:
            return self.parse_return_statement()
            
        # Parallel computing statements
        if self.current_token.type == TokenType.SPAWN:
            return self.parse_spawn_statement()
        if self.current_token.type == TokenType.ASYNC:
            return self.parse_async_statement()
            
        # Error handling
        if self.current_token.type == TokenType.RAISE:
            return self.parse_raise_statement()
            
        # Expression statement (default)
        return self.parse_expression_statement()
        
    def parse_auto_declaration(self) -> Dict:
        """Parse an auto variable declaration"""
        self.expect(TokenType.AUTO)
        
        name = self.current_token.value
        self.expect(TokenType.IDENTIFIER)
        
        self.expect(TokenType.ASSIGN)
        
        initializer = self.parse_expression()
        
        return {
            'type': 'AutoDeclaration',
            'name': name,
            'initializer': initializer
        }
        
    def parse_expression(self) -> Dict:
        """Parse an expression"""
        return self.parse_assignment()
        
    def parse_assignment(self) -> Dict:
        """Parse an assignment expression"""
        expr = self.parse_logical_or()
        
        if self.current_token.type in [TokenType.EQUAL, TokenType.PLUS_EQUAL, TokenType.MINUS_EQUAL, TokenType.STAR_EQUAL, TokenType.SLASH_EQUAL]:
            operator = self.current_token.type
            self.next()
            right = self.parse_assignment()  # Right-associative
            expr = {
                'type': 'AssignmentExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_logical_or(self) -> Dict:
        """Parse logical OR expression"""
        expr = self.parse_logical_and()
        
        while self.current_token.type == TokenType.OR:
            operator = self.current_token.type
            self.next()
            right = self.parse_logical_and()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_logical_and(self) -> Dict:
        """Parse logical AND expression"""
        expr = self.parse_equality()
        
        while self.current_token.type == TokenType.AND:
            operator = self.current_token.type
            self.next()
            right = self.parse_equality()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_equality(self) -> Dict:
        """Parse equality expression"""
        expr = self.parse_relational()
        
        while self.current_token.type in [TokenType.EQUAL_EQUAL, TokenType.NOT_EQUAL]:
            operator = self.current_token.type
            self.next()
            right = self.parse_relational()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_relational(self) -> Dict:
        """Parse relational expression"""
        expr = self.parse_additive()
        
        while self.current_token.type in [TokenType.LESS, TokenType.GREATER, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL]:
            operator = self.current_token.type
            self.next()
            right = self.parse_additive()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_additive(self) -> Dict:
        """Parse additive expression"""
        expr = self.parse_multiplicative()
        
        while self.current_token.type in [TokenType.PLUS, TokenType.MINUS]:
            operator = self.current_token.type
            self.next()
            right = self.parse_multiplicative()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_multiplicative(self) -> Dict:
        """Parse multiplicative expression"""
        expr = self.parse_unary()
        
        while self.current_token.type in [TokenType.STAR, TokenType.SLASH]:
            operator = self.current_token.type
            self.next()
            right = self.parse_unary()
            expr = {
                'type': 'BinaryExpression',
                'operator': operator,
                'left': expr,
                'right': right
            }
            
        return expr
        
    def parse_unary(self) -> Dict:
        """Parse unary expression"""
        if self.current_token.type in [TokenType.MINUS, TokenType.NOT]:
            operator = self.current_token.type
            self.next()
            operand = self.parse_unary()
            return {
                'type': 'UnaryExpression',
                'operator': operator,
                'operand': operand
            }
            
        return self.parse_primary()
        
    def parse_primary(self) -> Dict:
        """Parse a primary expression"""
        # Skip any comments
        self.skip_comments()
        
        token = self.current_token
        
        if token.type == TokenType.INTEGER:
            self.next()
            return {'type': 'IntegerLiteral', 'value': token.value}
            
        elif token.type == TokenType.FLOAT:
            self.next()
            return {'type': 'FloatLiteral', 'value': token.value}
            
        elif token.type == TokenType.STRING:
            self.next()
            return {'type': 'StringLiteral', 'value': token.value}
            
        elif token.type == TokenType.IDENTIFIER:
            self.next()
            expr = {'type': 'Identifier', 'name': token.value}
            
            while True:
                # Skip any comments
                self.skip_comments()
                
                if self.current_token.type == TokenType.LEFT_BRACKET:
                    # Array access or slice
                    if self.peek().type == TokenType.COLON:
                        expr = {
                            'type': 'ArraySliceExpression',
                            'array': expr,
                            'slice': self.parse_array_slice()
                        }
                    else:
                        expr = {
                            'type': 'ArrayAccessExpression',
                            'array': expr,
                            'access': self.parse_array_access()
                        }
                else:
                    break
                    
            return expr
            
        elif token.type == TokenType.LEFT_PAREN:
            self.next()  # Skip (
            expr = self.parse_expression()
            
            # Skip any comments before closing paren
            self.skip_comments()
            
            if self.current_token.type != TokenType.RIGHT_PAREN:
                raise SyntaxError(f"Expected ')', got {self.current_token.type.value}")
            self.next()  # Skip )
            return expr
            
        else:
            raise SyntaxError(f"Unexpected token {token.type.value}")
            
    def parse_array_slice(self) -> Dict:
        """Parse an array slice: arr[start:end:step]"""
        # Skip any comments before start expression
        self.skip_comments()
        
        start = None
        if self.current_token.type != TokenType.COLON:
            start = self.parse_expression()
        
        # Skip any comments before first colon
        self.skip_comments()
        
        if self.current_token.type != TokenType.COLON:
            raise SyntaxError(f"Expected ':' in array slice, got {self.current_token.type.value}")
        self.next()  # Skip :
        
        # Skip any comments before end expression
        self.skip_comments()
        
        end = None
        if self.current_token.type not in [TokenType.COLON, TokenType.RIGHT_BRACKET]:
            end = self.parse_expression()
        
        step = None
        if self.current_token.type == TokenType.COLON:
            self.next()  # Skip :
            
            # Skip any comments before step expression
            self.skip_comments()
            
            if self.current_token.type != TokenType.RIGHT_BRACKET:
                step = self.parse_expression()
        
        # Skip any comments before closing bracket
        self.skip_comments()
        
        if self.current_token.type != TokenType.RIGHT_BRACKET:
            raise SyntaxError(f"Expected ']' after array slice, got {self.current_token.type.value}")
        self.next()  # Skip ]
        
        return {
            'type': 'ArraySlice',
            'start': start,
            'end': end,
            'step': step
        }

    def parse_array_access(self) -> Dict:
        """Parse array access: arr[index]"""
        # Skip any comments before opening bracket
        self.skip_comments()
        
        if self.current_token.type != TokenType.LEFT_BRACKET:
            raise SyntaxError(f"Expected '[', got {self.current_token.type.value}")
        self.next()  # Skip [
        
        # Skip any comments before index expression
        self.skip_comments()
        
        # Parse index expression
        index = self.parse_expression()
        
        # Skip any comments before closing bracket
        self.skip_comments()
        
        if self.current_token.type != TokenType.RIGHT_BRACKET:
            raise SyntaxError(f"Expected ']' after array index, got {self.current_token.type.value}")
        self.next()  # Skip ]
        
        return {
            'type': 'ArrayAccess',
            'index': index
        }

    def parse_spawn_statement(self) -> Dict:
        """Parse a spawn statement"""
        self.expect(TokenType.SPAWN)
        
        expr = self.parse_expression()
        
        return {
            'type': 'SpawnStatement',
            'expression': expr
        }
        
    def parse_async_statement(self) -> Dict:
        """Parse an async statement"""
        self.expect(TokenType.ASYNC)
        
        # Parse block
        body = self.parse_block()
        
        return {
            'type': 'AsyncStatement',
            'body': body
        }
        
    def parse_range_expression(self) -> Dict:
        """Parse a range expression: range(start, end[, step])"""
        # Skip any comments before range keyword
        self.skip_comments()
        
        if self.current_token.type != TokenType.RANGE:
            raise SyntaxError(f"Expected 'range', got {self.current_token.type.value}")
        self.next()  # Skip range
        
        # Skip any comments after range keyword
        self.skip_comments()
        
        if self.current_token.type != TokenType.LEFT_PAREN:
            raise SyntaxError(f"Expected '(' after range, got {self.current_token.type.value}")
        self.next()  # Skip (
        
        # Skip any comments before start expression
        self.skip_comments()
        
        # Parse start expression
        start = self.parse_expression()
        
        # Skip any comments after start expression
        self.skip_comments()
        
        if self.current_token.type != TokenType.COMMA:
            raise SyntaxError(f"Expected ',' after range start, got {self.current_token.type.value}")
        self.next()  # Skip ,
        
        # Skip any comments before end expression
        self.skip_comments()
        
        # Parse end expression
        end = self.parse_expression()
        
        # Optional step parameter
        step = None
        if self.current_token.type == TokenType.COMMA:
            self.next()  # Skip ,
            
            # Skip any comments before step expression
            self.skip_comments()
            
            step = self.parse_expression()
        
        # Skip any comments before closing paren
        self.skip_comments()
        
        if self.current_token.type != TokenType.RIGHT_PAREN:
            raise SyntaxError(f"Expected ')' after range arguments, got {self.current_token.type.value}")
        self.next()  # Skip )
        
        return {
            'type': 'RangeExpression',
            'start': start,
            'end': end,
            'step': step
        }

    def parse_for_statement(self) -> Dict:
        """Parse a for statement"""
        # Skip any comments before 'for'
        self.skip_comments()
        
        if self.current_token.type != TokenType.FOR:
            raise SyntaxError(f"Expected 'for', got {self.current_token.type.value}")
        self.next()  # Skip for
        
        # Skip any comments before iterator variable
        self.skip_comments()
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected iterator variable name, got {self.current_token.type.value}")
        iterator = self.current_token.value
        self.next()
        
        # Skip any comments before 'in'
        self.skip_comments()
        
        if self.current_token.type != TokenType.IN:
            raise SyntaxError(f"Expected 'in', got {self.current_token.type.value}")
        self.next()  # Skip in
        
        # Skip any comments before iterable expression
        self.skip_comments()
        
        # Parse the iterable expression
        if self.current_token.type == TokenType.RANGE:
            iterable = self.parse_range_expression()
        else:
            iterable = self.parse_expression()
        
        # Skip any comments before body
        self.skip_comments()
        
        # Parse the loop body
        body = self.parse_block()
        
        return {
            'type': 'ForStatement',
            'iterator': iterator,
            'iterable': iterable,
            'body': body
        }
        
    def parse_if_statement(self) -> Dict:
        """Parse an if statement"""
        self.expect(TokenType.IF)
        
        condition = self.parse_expression()
        
        then_branch = self.parse_block()
        
        else_branch = None
        if self.current_token.type == TokenType.ELSE:
            self.next()
            if self.current_token.type == TokenType.IF:
                else_branch = self.parse_if_statement()  # Handle 'else if'
            else:
                else_branch = self.parse_block()
                
        return {
            'type': 'IfStatement',
            'condition': condition,
            'thenBranch': then_branch,
            'elseBranch': else_branch
        }
        
    def parse_while_statement(self) -> Dict:
        """Parse a while statement"""
        self.expect(TokenType.WHILE)
        
        condition = self.parse_expression()
        
        body = self.parse_block()
        
        return {
            'type': 'WhileStatement',
            'condition': condition,
            'body': body
        }
        
    def parse_return_statement(self) -> Dict:
        """Parse a return statement"""
        self.next()  # Skip 'ret'
        
        # Parse return value if present
        value = None
        if self.current_token.type != TokenType.SEMICOLON:
            value = self.parse_expression()
            
        return {
            'type': 'ReturnStatement',
            'value': value
        }
        
    def parse_expression_statement(self) -> Dict:
        """Parse an expression statement"""
        expr = self.parse_expression()
        
        return {
            'type': 'ExpressionStatement',
            'expression': expr
        }
        
    def parse_member_access(self, name: str) -> Dict:
        """Parse a member access"""
        self.expect(TokenType.DOT)
        member = self.current_token.value
        self.expect(TokenType.IDENTIFIER)
        
        # Check for method call
        if self.current_token.type == TokenType.LEFT_PAREN:
            return self.parse_function_call(f"{name}.{member}")
            
        return {
            'type': 'MemberAccess',
            'object': {'type': 'Identifier', 'name': name},
            'member': member
        }
        
    def parse_variable_declaration(self) -> Dict:
        """Parse a variable declaration"""
        # Handle 'let' or 'auto' keyword
        is_auto = self.current_token.type == TokenType.AUTO
        self.next()
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected variable name, got {self.current_token.type.value}")
        name = self.current_token.value
        self.next()
        
        # Parse type annotation if present
        var_type = None
        if self.current_token.type == TokenType.COLON:
            self.next()  # Skip :
            var_type = self.parse_type_expression()
            
        # Parse initializer if present
        initializer = None
        if self.current_token.type == TokenType.EQUAL:
            self.next()  # Skip =
            initializer = self.parse_expression()
            
        return {
            'type': 'VariableDeclaration',
            'name': name,
            'varType': var_type,
            'initializer': initializer,
            'isAuto': is_auto
        }
        
    def parse_raise_statement(self) -> Dict:
        """Parse a raise statement"""
        self.next()  # Skip 'raise'
        
        # Parse error expression
        error = self.parse_expression()
        
        return {
            'type': 'RaiseStatement',
            'error': error
        }
        
    def parse_spawn_statement(self) -> Dict:
        """Parse a spawn statement"""
        self.expect(TokenType.SPAWN)
        
        expr = self.parse_expression()
        
        return {
            'type': 'SpawnStatement',
            'expression': expr
        }
        
    def parse_async_statement(self) -> Dict:
        """Parse an async statement"""
        self.expect(TokenType.ASYNC)
        
        # Parse block
        body = self.parse_block()
        
        return {
            'type': 'AsyncStatement',
            'body': body
        }
        
    def parse_decorator(self) -> Dict:
        """Parse a decorator"""
        # Skip any comments before @
        self.skip_comments()
        
        if self.current_token.type != TokenType.AT:
            raise SyntaxError(f"Expected '@', got {self.current_token.type.value}")
        self.next()  # Skip @
        
        # Skip any comments between @ and identifier
        self.skip_comments()
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected decorator name, got {self.current_token.type.value}")
        name = self.current_token.value
        self.next()
        
        # Skip any comments after identifier
        self.skip_comments()
        
        # Parse decorator arguments if present
        args = []
        if self.current_token.type == TokenType.LEFT_PAREN:
            self.next()  # Skip (
            
            # Skip any comments after (
            self.skip_comments()
            
            if self.current_token.type != TokenType.RIGHT_PAREN:
                while True:
                    # Skip any comments before argument
                    self.skip_comments()
                    
                    args.append(self.parse_expression())
                    
                    # Skip any comments after argument
                    self.skip_comments()
                    
                    if self.current_token.type == TokenType.RIGHT_PAREN:
                        break
                        
                    if self.current_token.type != TokenType.COMMA:
                        raise SyntaxError(f"Expected ',' or ')', got {self.current_token.type.value}")
                    self.next()  # Skip ,
                    
            self.next()  # Skip )
            
        return {
            'type': 'Decorator',
            'name': name,
            'arguments': args
        }
        
    def parse_import(self) -> Dict:
        """Parse an import statement"""
        # Skip the import keyword
        self.expect(TokenType.IMPORT)
        
        # Parse the module string
        if self.current_token.type != TokenType.STRING:
            raise SyntaxError(f"Expected string literal for import module, got {self.current_token.type.value}")
        module = self.current_token.value.strip('"\'')
        self.next()
        
        # Parse optional header file
        header = None
        if self.current_token.type == TokenType.STRING:
            header = self.current_token.value.strip('"\'')
            self.next()
            
        # Expect semicolon
        self.expect(TokenType.SEMICOLON)
        
        return {
            'type': 'ImportDeclaration',
            'module': module,
            'header': header
        }

    def parse_interface_declaration(self) -> Dict:
        """Parse an interface declaration"""
        self.expect(TokenType.INTERFACE)
        
        if self.current_token.type != TokenType.IDENTIFIER:
            raise SyntaxError(f"Expected interface name, got {self.current_token.type.value}")
        name = self.current_token.value
        self.next()
        
        self.expect(TokenType.LEFT_BRACE)
        
        methods = []
        while self.current_token.type != TokenType.RIGHT_BRACE:
            self.skip_comments()
            if self.current_token.type == TokenType.ABSTRACT:
                self.next()
                methods.append(self.parse_function_declaration())
            else:
                raise SyntaxError(f"Expected abstract method declaration, got {self.current_token.type.value}")
        
        self.expect(TokenType.RIGHT_BRACE)
        
        return {
            'type': 'InterfaceDeclaration',
            'name': name,
            'methods': methods
        }