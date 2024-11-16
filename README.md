# MetaForge-Compiler

MetaForge Compiler (MFC) is the native compiler for the **MetaForge** programming language, designed to provide efficient and seamless compilation for your MetaForge projects. It supports cross-platform compilation and offers various options to customize the output.

## Features
- Native compilation for the MetaForge language.
- Support for cross-platform targets (e.g., Windows, Linux, MacOS and FreeBSD system like Ps* system).
- Adjustable architecture options (e.g., x64, ARM).
- Verbose output for debugging and monitoring the compilation process.

## Getting Started
### Prerequisites
Ensure you have Python installed on your system (Python 3.13 or higher is recommended).

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/seregonwar/MetaForge-Compiler.git
   cd MetaForge-Compiler
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Usage
To compile a MetaForge source file, use the following command structure:

```bash
python src/compile_metaforge.py <source_file> -o <output_file> [options]
```

#### Example Command
The following example compiles a MetaForge file named `hello_world.mf`:
```bash
python src/compile_metaforge.py examples/hello_world.mf -o build/hello_world.exe --platform windows --arch x64 -v
```

#### Command Breakdown:
- `<source_file>`: Path to the MetaForge source file to compile (e.g., `examples/hello_world.mf`).
- `-o <output_file>`: Specifies the output file path (e.g., `build/hello_world.exe`).
- `--platform`: Sets the target platform (`windows`, `linux`, etc.).
- `--arch`: Specifies the architecture (`x64`, `x86`, `arm`).
- `-v`: Enables verbose output for additional compilation details.

### Additional Options
Run the following command to view all available options:
```bash
python src/compile_metaforge.py --help
```

## Compilation Methods in **MetaForge**

MetaForge provides three compilation methods, each tailored to specific project needs.

---

### 1. **Native Compilation**  
- **Description**: Uses MetaForge’s native compiler to directly convert `.mf` files into `.exe` executables.  
- **Features**:  
  - Direct compilation without intermediaries.  
  - **Pros**: Maximum stability, high performance, and secure output.  
  - **Use Case**: Best suited for standalone programs and native applications.  

---

### 2. **Compilation via GCC**  
- **Description**: Utilizes the GCC compiler through a multi-step process:  
  1. Converts the `.mf` file into an intermediate C file.  
  2. Compiles the C file into libraries (DLL) or object files (Obj).  
  3. Optionally links the object files to produce an executable.  
- **Features**:  
  - **Pros**: Ideal for creating support libraries or reusable components.  
  - **Cons**: Not recommended for complete programs due to reduced stability and security compared to native compilation.  
  - **Use Case**: Useful for building add-ons or ensuring interoperability with C-based projects.  

---

### 3. **Compilation via Python**  
- **Description**: Similar to the GCC method but uses Python as the intermediary language.  
  - Python translates the `.mf` file into executable or web-compatible code, with some performance trade-offs.  
  - Since Python is a higher-level language than MetaForge and C, this results in a performance drop (up to 70% of MetaForge’s potential).  
- **Features**:  
  - **Pros**: Essential for web applications and compatible with technologies such as WebAssembly.  
  - **Cons**: Higher overhead and lower performance compared to other methods.  
  - **Use Case**: Designed to enable MetaForge in web environments and applications requiring online integration.  

---
## Example Directory Structure
```plaintext
MetaForge-Compiler/
├── examples/
│   └── hello_world.mf       # Example MetaForge program
├── src/
│   └── compile_metaforge.py # Compiler script
├── build/                   # Output directory (generated after compilation)
├── requirements.txt         # Python dependencies
└── readme.md                # Documentation
```

## Contributing
Contributions are welcome! If you'd like to improve the compiler or add new features, feel free to fork the repository and submit a pull request.

## License
This project is licensed under the [MIT License](LICENSE). For commercial use of the MetaForge language, consult the license terms included in the MetaForge specification.
