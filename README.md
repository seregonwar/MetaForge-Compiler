# MetaForge-Compiler

MetaForge Compiler (MFC) is the native compiler for the **MetaForge** programming language, designed to provide efficient and seamless compilation for your MetaForge projects. It supports cross-platform compilation and offers various options to customize the output.

## Features
- Native compilation for the MetaForge language.
- Support for cross-platform targets (e.g., Windows, Linux).
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
