from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import logging

@dataclass
class ClassInfo:
    name: str
    superclass: Optional[str]
    interfaces: List[str]
    methods: Dict[str, 'MethodInfo']
    fields: Dict[str, 'FieldInfo']
    vtable: Dict[str, int]  # Method name to vtable index mapping
    vtable_size: int

@dataclass
class MethodInfo:
    name: str
    visibility: str
    is_static: bool
    is_abstract: bool
    is_override: bool
    parameters: List[Dict]
    return_type: Optional[str]
    body: Optional[List[Dict]]
    offset: int  # Offset in vtable or static area

@dataclass
class FieldInfo:
    name: str
    visibility: str
    is_static: bool
    field_type: str
    offset: int  # Offset in instance or static area

class OOPGenerator:
    def __init__(self):
        self.classes: Dict[str, ClassInfo] = {}
        self.interfaces: Dict[str, Set[str]] = {}  # Interface name to method names
        self.current_class: Optional[ClassInfo] = None
        
    def process_ast(self, ast: Dict) -> None:
        """Process the AST and collect class/interface information"""
        for decl in ast['declarations']:
            if decl['type'] == 'ClassDeclaration':
                self._process_class_declaration(decl)
            elif decl['type'] == 'InterfaceDeclaration':
                self._process_interface_declaration(decl)
                
        # After collecting all class info, build vtables
        self._build_vtables()
        
    def _process_class_declaration(self, decl: Dict) -> None:
        """Process a class declaration and collect its information"""
        class_name = decl['name']
        superclass = decl['superclass']
        interfaces = decl['interfaces']
        
        # Create class info
        class_info = ClassInfo(
            name=class_name,
            superclass=superclass,
            interfaces=interfaces,
            methods={},
            fields={},
            vtable={},
            vtable_size=0
        )
        
        self.current_class = class_info
        
        # Process class body
        field_offset = 0
        static_offset = 0
        
        for member in decl['body']:
            if member['type'] == 'MethodDeclaration':
                method_info = MethodInfo(
                    name=member['name'],
                    visibility=member['visibility'],
                    is_static=member['isStatic'],
                    is_abstract=member['isAbstract'],
                    is_override=member['isOverride'],
                    parameters=member['parameters'],
                    return_type=member['returnType'],
                    body=member['body'],
                    offset=0  # Will be set when building vtable
                )
                class_info.methods[member['name']] = method_info
                
            elif member['type'] == 'FieldDeclaration':
                field_info = FieldInfo(
                    name=member['name'],
                    visibility=member['visibility'],
                    is_static=member['isStatic'],
                    field_type=member['fieldType'],
                    offset=static_offset if member['isStatic'] else field_offset
                )
                
                # Update offsets
                if member['isStatic']:
                    static_offset += self._get_type_size(member['fieldType'])
                else:
                    field_offset += self._get_type_size(member['fieldType'])
                    
                class_info.fields[member['name']] = field_info
                
        self.classes[class_name] = class_info
        self.current_class = None
        
    def _process_interface_declaration(self, decl: Dict) -> None:
        """Process an interface declaration and collect its method signatures"""
        interface_name = decl['name']
        methods = set()
        
        for method in decl['methods']:
            methods.add(method['name'])
            
        # Add methods from extended interfaces
        for extended in decl['extends']:
            if extended in self.interfaces:
                methods.update(self.interfaces[extended])
                
        self.interfaces[interface_name] = methods
        
    def _build_vtables(self) -> None:
        """Build virtual method tables for all classes"""
        for class_name, class_info in self.classes.items():
            vtable_index = 0
            seen_methods = set()
            
            # First, add methods from superclass
            if class_info.superclass:
                super_info = self.classes[class_info.superclass]
                class_info.vtable.update(super_info.vtable)
                vtable_index = super_info.vtable_size
                seen_methods.update(super_info.vtable.keys())
            
            # Then add interface methods
            for interface in class_info.interfaces:
                if interface in self.interfaces:
                    for method in self.interfaces[interface]:
                        if method not in seen_methods:
                            class_info.vtable[method] = vtable_index
                            vtable_index += 1
                            seen_methods.add(method)
            
            # Finally add class methods
            for method_name, method_info in class_info.methods.items():
                if not method_info.is_static and method_name not in seen_methods:
                    class_info.vtable[method_name] = vtable_index
                    method_info.offset = vtable_index
                    vtable_index += 1
                    
            class_info.vtable_size = vtable_index
            
    def _get_type_size(self, type_name: str) -> int:
        """Get size in bytes for a type"""
        sizes = {
            'i8': 1,
            'i16': 2,
            'i32': 4,
            'i64': 8,
            'u8': 1,
            'u16': 2,
            'u32': 4,
            'u64': 8,
            'f32': 4,
            'f64': 8,
            'bool': 1,
            'ptr': 8,
            'string': 8  # String reference
        }
        return sizes.get(type_name, 8)  # Default to pointer size for objects
        
    def generate_class_layout(self, class_name: str) -> bytes:
        """Generate memory layout for a class"""
        class_info = self.classes[class_name]
        
        # Class layout:
        # - vtable pointer (8 bytes)
        # - instance fields (variable size)
        layout = bytearray(8)  # vtable pointer
        
        # Add instance fields
        for field_name, field_info in sorted(class_info.fields.items(), key=lambda x: x[1].offset):
            if not field_info.is_static:
                size = self._get_type_size(field_info.field_type)
                layout.extend(bytes(size))
                
        return bytes(layout)
        
    def generate_vtable(self, class_name: str) -> bytes:
        """Generate vtable for a class"""
        class_info = self.classes[class_name]
        
        # VTable layout:
        # - method count (8 bytes)
        # - method pointers (8 bytes each)
        vtable = bytearray(8)  # method count
        
        # Add method pointers (will be filled in by linker)
        for _ in range(class_info.vtable_size):
            vtable.extend(bytes(8))
            
        return bytes(vtable)
        
    def generate_static_area(self, class_name: str) -> bytes:
        """Generate static area for a class"""
        class_info = self.classes[class_name]
        static_size = 0
        
        # Calculate total size of static fields
        for field_info in class_info.fields.values():
            if field_info.is_static:
                static_size += self._get_type_size(field_info.field_type)
                
        return bytes(static_size)  # Initialize to zero
