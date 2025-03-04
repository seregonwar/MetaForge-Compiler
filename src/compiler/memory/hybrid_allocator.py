from enum import Enum, auto
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging
import ctypes
import mmap

class MemoryStrategy(Enum):
    MANUAL = auto()      # Like C/C++
    AUTOMATIC = auto()   # Like Python/Java
    HYBRID = auto()      # Smart hybrid approach
    ARENA = auto()       # Arena allocation for temporary objects
    POOL = auto()        # Object pooling for frequently allocated types

@dataclass
class MemoryBlock:
    address: int
    size: int
    is_free: bool
    strategy: MemoryStrategy
    ref_count: int = 0
    last_access: float = 0
    generation: int = 0

class ObjectLifetime(Enum):
    TEMPORARY = auto()   # Short-lived objects (stack or arena)
    MEDIUM = auto()      # Medium-lived objects (hybrid management)
    PERMANENT = auto()   # Long-lived objects (manual management)
    POOLED = auto()      # Objects suitable for pooling

@dataclass
class TypeInfo:
    name: str
    size: int
    lifetime: ObjectLifetime
    pool_size: Optional[int] = None  # For pooled objects

class HybridAllocator:
    def __init__(self, heap_size: int = 1024 * 1024 * 1024):  # 1GB default
        self.heap_size = heap_size
        self.blocks: List[MemoryBlock] = []
        self.type_info: Dict[str, TypeInfo] = {}
        self.object_pools: Dict[str, List[int]] = {}  # type -> list of addresses
        self.arenas: List[mmap.mmap] = []
        self.current_arena = None
        self.arena_size = 1024 * 1024  # 1MB
        
        # Initialize memory map
        self.memory = mmap.mmap(-1, heap_size)
        self.blocks.append(MemoryBlock(0, heap_size, True, MemoryStrategy.MANUAL))
        
        logging.info(f"Initialized hybrid allocator with {heap_size/1024/1024:.1f}MB heap")
        
    def register_type(self, name: str, size: int, lifetime: ObjectLifetime, pool_size: Optional[int] = None):
        """Register a type for optimized memory management"""
        self.type_info[name] = TypeInfo(name, size, lifetime, pool_size)
        
        if lifetime == ObjectLifetime.POOLED and pool_size:
            self._init_object_pool(name, size, pool_size)
            
        logging.debug(f"Registered type {name} with {lifetime.name} lifetime")
        
    def _init_object_pool(self, type_name: str, obj_size: int, pool_size: int):
        """Initialize an object pool for a type"""
        total_size = obj_size * pool_size
        pool_addr = self._allocate_block(total_size, MemoryStrategy.POOL)
        
        if pool_addr is None:
            logging.error(f"Failed to allocate pool for type {type_name}")
            return
            
        # Initialize pool
        self.object_pools[type_name] = []
        for i in range(pool_size):
            addr = pool_addr + (i * obj_size)
            self.object_pools[type_name].append(addr)
            
        logging.debug(f"Initialized pool for {type_name} with {pool_size} objects")
        
    def allocate(self, size: int, type_name: Optional[str] = None) -> Optional[int]:
        """Allocate memory using the most appropriate strategy"""
        if type_name and type_name in self.type_info:
            type_info = self.type_info[type_name]
            
            if type_info.lifetime == ObjectLifetime.POOLED:
                return self._allocate_from_pool(type_name)
            elif type_info.lifetime == ObjectLifetime.TEMPORARY:
                return self._allocate_from_arena(size)
                
        # Default to hybrid allocation
        return self._allocate_block(size, MemoryStrategy.HYBRID)
        
    def _allocate_from_pool(self, type_name: str) -> Optional[int]:
        """Allocate an object from its type pool"""
        if type_name not in self.object_pools or not self.object_pools[type_name]:
            logging.warning(f"Object pool for {type_name} is empty")
            return None
            
        addr = self.object_pools[type_name].pop()
        logging.debug(f"Allocated {type_name} from pool at {addr}")
        return addr
        
    def _allocate_from_arena(self, size: int) -> Optional[int]:
        """Allocate from the current arena or create new one"""
        if self.current_arena is None or size > self.arena_size:
            self.current_arena = mmap.mmap(-1, self.arena_size)
            self.arenas.append(self.current_arena)
            
        # Simple bump allocator for arena
        addr = id(self.current_arena) + self.current_arena.tell()
        self.current_arena.seek(size, 1)
        return addr
        
    def _allocate_block(self, size: int, strategy: MemoryStrategy) -> Optional[int]:
        """Allocate a block of memory using the specified strategy"""
        # Find best fit block
        best_block = None
        best_index = -1
        
        for i, block in enumerate(self.blocks):
            if block.is_free and block.size >= size:
                if best_block is None or block.size < best_block.size:
                    best_block = block
                    best_index = i
                    
        if best_block is None:
            logging.error(f"Failed to allocate {size} bytes: No suitable block found")
            return None
            
        # Split block if significantly larger
        if best_block.size > size + 64:  # Minimum split threshold
            remaining_size = best_block.size - size
            self.blocks.insert(best_index + 1, 
                             MemoryBlock(best_block.address + size,
                                       remaining_size,
                                       True,
                                       MemoryStrategy.MANUAL))
            best_block.size = size
            
        best_block.is_free = False
        best_block.strategy = strategy
        best_block.ref_count = 1
        
        logging.debug(f"Allocated {size} bytes at {best_block.address} using {strategy.name}")
        return best_block.address
        
    def free(self, address: int):
        """Free allocated memory"""
        for i, block in enumerate(self.blocks):
            if block.address == address:
                if block.strategy == MemoryStrategy.POOL:
                    # Return to pool
                    for type_name, type_info in self.type_info.items():
                        if type_info.lifetime == ObjectLifetime.POOLED:
                            pool_start = min(self.object_pools[type_name])
                            pool_end = pool_start + (type_info.size * type_info.pool_size)
                            if pool_start <= address < pool_end:
                                self.object_pools[type_name].append(address)
                                logging.debug(f"Returned object to {type_name} pool")
                                return
                                
                elif block.strategy == MemoryStrategy.HYBRID:
                    block.ref_count -= 1
                    if block.ref_count > 0:
                        logging.debug(f"Decremented ref count for block at {address}")
                        return
                        
                # Mark block as free and merge adjacent free blocks
                block.is_free = True
                block.ref_count = 0
                self._merge_adjacent_blocks(i)
                logging.debug(f"Freed block at {address}")
                return
                
        logging.warning(f"Attempted to free invalid address: {address}")
        
    def _merge_adjacent_blocks(self, index: int):
        """Merge adjacent free blocks"""
        while index < len(self.blocks) - 1:
            current = self.blocks[index]
            next_block = self.blocks[index + 1]
            
            if current.is_free and next_block.is_free:
                current.size += next_block.size
                self.blocks.pop(index + 1)
            else:
                break
                
    def increment_ref(self, address: int):
        """Increment reference count for hybrid-managed block"""
        for block in self.blocks:
            if block.address == address and block.strategy == MemoryStrategy.HYBRID:
                block.ref_count += 1
                logging.debug(f"Incremented ref count for block at {address}")
                return
                
    def collect_garbage(self):
        """Run garbage collection on hybrid-managed blocks"""
        freed = 0
        for block in self.blocks:
            if not block.is_free and block.strategy == MemoryStrategy.HYBRID:
                if block.ref_count == 0:
                    block.is_free = True
                    freed += block.size
                    
        if freed > 0:
            logging.info(f"Garbage collection freed {freed/1024:.1f}KB")
            
    def defragment(self):
        """Defragment memory by moving blocks to eliminate fragmentation"""
        if not self.blocks:
            return
            
        # Sort blocks by address
        self.blocks.sort(key=lambda b: b.address)
        
        # Compact blocks
        write_ptr = 0
        for block in self.blocks:
            if not block.is_free:
                if block.address != write_ptr:
                    # Move block data
                    self.memory.move(write_ptr, block.address, block.size)
                    block.address = write_ptr
                write_ptr += block.size
                
        # Create single free block at end if space remains
        if write_ptr < self.heap_size:
            self.blocks = [b for b in self.blocks if not b.is_free]
            self.blocks.append(MemoryBlock(write_ptr,
                                         self.heap_size - write_ptr,
                                         True,
                                         MemoryStrategy.MANUAL))
                                         
        logging.info("Memory defragmentation complete")
