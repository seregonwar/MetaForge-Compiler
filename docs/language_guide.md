# MetaForge Language Guide
## Core Language Features

### 1. Memory Management

MetaForge offers three memory management strategies that can be used together:

```metaforge
// Automatic memory management (like Python/Java)
auto x = 42
auto list = [1, 2, 3]

// Manual memory management (like C/C++)
manual int* ptr = alloc(sizeof(int))
*ptr = 100
dealloc(ptr)

// Hybrid memory management (reference counted)
hybrid Vector vec = new Vector(1000)
vec.push(1)  // Automatically freed when ref count hits 0
```

### 2. Multi-Syntax Support

MetaForge allows you to write code in different syntax styles:

```metaforge
# Python-style
def calculate_sum(numbers):
    return sum(x for x in numbers)

// C-style
int factorial(int n) {
    if (n <= 1) return 1;
    return n * factorial(n - 1);
}

// Rust-style
fn quick_sort<T: Ord>(mut arr: Vec<T>) -> Vec<T> {
    if arr.len() <= 1 { return arr; }
    let pivot = arr.pop().unwrap();
    let (left, right): (Vec<T>, Vec<T>) = arr.into_iter()
        .partition(|x| x <= &pivot);
    [quick_sort(left), vec![pivot], quick_sort(right)].concat()
}
```

### 3. Type System

#### Basic Types
```metaforge
int x = 42              // Integer
float y = 3.14         // Floating point
bool flag = true       // Boolean
string text = "Hello"  // String
char c = 'A'          // Character
```

#### Advanced Types
```metaforge
// Arrays
int[] numbers = [1, 2, 3]
int[3] fixed_array = [1, 2, 3]

// Tuples
(int, string) pair = (42, "answer")

// Optional types
int? maybe_number = null

// Generic types
Vector<int> vec = new Vector()
```

### 4. Memory Optimization Features

#### Object Pooling
```metaforge
@pool_size(1000)  // Use object pooling
class Particle {
    float x, y, z
    float velocity
}

// Objects automatically drawn from/returned to pool
auto particle = new Particle()
```

#### Arena Allocation
```metaforge
@arena_allocate  // Use arena allocation for temporary objects
func process_data(data: float[]) {
    auto temp = new Vector<float>()
    // temp automatically freed when function returns
}
```

### 5. Classes and Objects

```metaforge
class Point {
    float x, y
    
    // Constructor
    func __init__(x: float, y: float) {
        self.x = x
        self.y = y
    }
    
    // Method
    func distance_to(other: Point) -> float {
        return sqrt((self.x - other.x)^2 + (self.y - other.y)^2)
    }
}

// Usage
auto p1 = new Point(0, 0)
auto p2 = new Point(3, 4)
auto dist = p1.distance_to(p2)  // 5.0
```

### 6. Error Handling

```metaforge
// Try-catch blocks
try {
    auto result = risky_operation()
} catch Error e {
    print("Error:", e.message)
} finally {
    cleanup()
}

// Result type (like Rust)
func divide(a: int, b: int) -> Result<float, string> {
    if b == 0 {
        return Err("Division by zero")
    }
    return Ok(a / b)
}
```

### 7. Concurrency

```metaforge
// Async/await
async func fetch_data() -> string {
    auto response = await http.get("https://api.example.com")
    return response.text
}

// Parallel execution
@parallel
func process_array(arr: float[]) {
    if arr.length < 1000 {
        return sequential_process(arr)
    }
    
    auto mid = arr.length / 2
    auto left = arr[0:mid]
    auto right = arr[mid:]
    
    // Spawn parallel tasks
    auto left_result = spawn process_array(left)
    auto right_result = spawn process_array(right)
    
    // Wait for results
    sync
    return combine(left_result, right_result)
}
```

### 8. Smart Pointers and RAII

```metaforge
class FileHandle {
    manual File* ptr
    
    func __init__(path: string) {
        self.ptr = open_file(path)
    }
    
    func __del__() {
        if self.ptr != null {
            close_file(self.ptr)
        }
    }
}

// File automatically closed when handle goes out of scope
func process_file(path: string) {
    auto handle = new FileHandle(path)
    // work with file...
}  // file closed here
```

## Best Practices

1. **Memory Management**
   - Use `auto` for most variables
   - Use `manual` only when you need precise control
   - Use `hybrid` for shared resources
   - Use `@pool_size` for frequently allocated objects
   - Use `@arena_allocate` for temporary calculations

2. **Type Safety**
   - Use explicit types for function parameters
   - Use optional types (`?`) instead of null
   - Use Result for error handling

3. **Performance**
   - Use appropriate memory management strategy
   - Consider object pooling for small, frequent allocations
   - Use arena allocation for temporary objects
   - Use parallel execution for CPU-intensive tasks

4. **Code Organization**
   - One class per file
   - Use modules to group related functionality
   - Follow consistent syntax style within a module

## Common Patterns

### Builder Pattern
```metaforge
class QueryBuilder {
    string table
    string[] columns
    string where_clause
    
    func select(columns: string[]) -> Self {
        self.columns = columns
        return self
    }
    
    func from(table: string) -> Self {
        self.table = table
        return self
    }
    
    func where(clause: string) -> Self {
        self.where_clause = clause
        return self
    }
    
    func build() -> string {
        return "SELECT ${columns.join(',')} FROM ${table} WHERE ${where_clause}"
    }
}
```

### Factory Pattern
```metaforge
interface Shape {
    func area() -> float
}

class Circle : Shape {
    float radius
    
    func area() -> float {
        return PI * radius * radius
    }
}

class ShapeFactory {
    static func create(type: string, params: float[]) -> Shape {
        switch type {
            case "circle":
                return new Circle(params[0])
            case "rectangle":
                return new Rectangle(params[0], params[1])
            default:
                raise Error("Unknown shape type")
        }
    }
}
```

### Observer Pattern
```metaforge
interface Observer {
    func update(data: any)
}

class Subject {
    hybrid Vector<Observer> observers
    
    func attach(observer: Observer) {
        observers.push(observer)
    }
    
    func notify(data: any) {
        for observer in observers {
            observer.update(data)
        }
    }
}
```

## Example Projects

Check out the `examples/` directory for complete example projects:
- `basic_examples.mf`: Basic language features
- `data_structures.mf`: Common data structure implementations
- `algorithms.mf`: Algorithm implementations
