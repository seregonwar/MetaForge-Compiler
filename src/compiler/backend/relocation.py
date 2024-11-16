from dataclasses import dataclass
from typing import List, Dict, Set
from enum import Enum

class RelocationType(Enum):
    REL32 = 0   # 32-bit relative
    DIR64 = 1   # 64-bit direct 
    REL64 = 2   # 64-bit relative
    
@dataclass
class RelocationEntry:
    offset: int     # Offset in section
    type: RelocationType
    symbol: str     # Target symbol name
    addend: int = 0 # Value to add

class RelocationBlock:
    def __init__(self, rva: int):
        self.rva = rva  # Base RVA of block
        self.entries: List[tuple[int, int]] = []  # [(offset, type), ...]
        
    def add_entry(self, offset: int, type: int):
        self.entries.append((offset, type))
        
    def get_size(self) -> int:
        return 8 + len(self.entries) * 2  # Header + entries
        
    def serialize(self) -> bytes:
        # Block header
        data = bytearray()
        data.extend(self.rva.to_bytes(4, 'little'))
        data.extend(self.get_size().to_bytes(4, 'little'))
        
        # Entries
        for offset, type in self.entries:
            entry = (type << 12) | (offset & 0xFFF)
            data.extend(entry.to_bytes(2, 'little'))
            
        return bytes(data)

class RelocationTable:
    def __init__(self):
        self.blocks: List[RelocationBlock] = []
        
    def add_relocation(self, rva: int, type: int):
        """Adds a relocation"""
        # Find appropriate block
        block_rva = rva & ~0xFFF  # Align to 4KB
        block = self._find_block(block_rva)
        if not block:
            block = RelocationBlock(block_rva)
            self.blocks.append(block)
            
        # Add the entry
        block.add_entry(rva & 0xFFF, type)
        
    def _find_block(self, rva: int) -> RelocationBlock:
        """Finds block for an RVA"""
        for block in self.blocks:
            if block.rva == rva:
                return block
        return None
        
    def serialize(self) -> bytes:
        """Serializes the relocation table"""
        data = bytearray()
        
        # Write all blocks
        for block in sorted(self.blocks, key=lambda b: b.rva):
            data.extend(block.serialize())
            
        return bytes(data)

class RelocationHandler:
    def __init__(self):
        self.relocations: List[RelocationEntry] = []
        self.processed: Set[str] = set()
        
    def add_relocation(self, entry: RelocationEntry):
        """Adds a relocation to process"""
        self.relocations.append(entry)
        
    def process_relocations(self, symbols: Dict[str, int]) -> RelocationTable:
        """Processes relocations and generates table"""
        table = RelocationTable()
        
        for reloc in self.relocations:
            if reloc.symbol not in symbols:
                raise Exception(f"Undefined symbol in relocation: {reloc.symbol}")
                
            target = symbols[reloc.symbol] + reloc.addend
            
            if reloc.type == RelocationType.REL32:
                # 32-bit relative relocation
                table.add_relocation(reloc.offset, 0x3)  # IMAGE_REL_BASED_HIGHLOW
            elif reloc.type == RelocationType.DIR64:
                # 64-bit direct relocation
                table.add_relocation(reloc.offset, 0xA)  # IMAGE_REL_BASED_DIR64
                
        return table