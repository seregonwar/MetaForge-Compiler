from pathlib import Path
from typing import Dict

# Base template for DLL
DLL_TEMPLATE = """
#define UMDF_USING_NTSTATUS
#define WIN32_NO_STATUS

#include <windows.h>
#include <winternl.h>
#include <ntstatus.h>

#pragma comment(lib, "ntdll.lib")

// Forward declarations
{forward_declarations}

// Global variables
{globals}

// DLL entry point
BOOL WINAPI DllMain(HINSTANCE hinstDLL, DWORD fdwReason, LPVOID lpvReserved) {{
    switch (fdwReason) {{
        case DLL_PROCESS_ATTACH:
            {dll_init}
            break;
        case DLL_PROCESS_DETACH:
            {dll_cleanup}
            break;
    }}
    return TRUE;
}}

// Generated declarations
{declarations}
"""

# Base template for EXE
EXE_TEMPLATE = """
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

// Forward declarations and imports
{forward_declarations}

// Global variables
{globals}

// Generated declarations
{declarations}
"""

def get_template(output_type: str) -> str:
    """
    Returns the appropriate template based on output type
    
    Args:
        output_type: "dll" or "exe"
        
    Returns:
        Template string
    """
    if output_type == "dll":
        return DLL_TEMPLATE
    elif output_type == "exe":
        return EXE_TEMPLATE
    else:
        raise ValueError(f"Invalid output type: {output_type}")

# Template for functions
FUNCTION_TEMPLATE = """
{export_spec}{calling_conv} {return_type} {name}({params}) {{
    {body}
}}
"""

# Template for structures
STRUCT_TEMPLATE = """
typedef struct _{name} {{
    {fields}
}} {name};
"""

# Template for enums
ENUM_TEMPLATE = """
typedef enum _{name} {{
    {values}
}} {name};
"""

# MetaForge to C type mapping
TYPE_MAPPING = {
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
    'bool': 'BOOL',
    'ptr': 'LPVOID',
    'key': 'HCRYPTKEY',
    'cipher': 'HCRYPTPROV',
    'hash': 'HCRYPTHASH',
    'bytes': 'BYTE*',
    'stream': 'FILE*'
}

def get_c_type(mf_type: str) -> str:
    """Converts a MetaForge type to corresponding C type"""
    return TYPE_MAPPING.get(mf_type, mf_type)