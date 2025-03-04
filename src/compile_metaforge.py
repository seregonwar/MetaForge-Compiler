from pathlib import Path
import sys
import argparse
import logging
import ctypes
import os
from typing import Dict

from compiler.pipeline import CompilationPipeline, CompilationContext
from compiler.diagnostics import DiagnosticEmitter
from compiler.optimization import OptimizationLevel
from compiler.backend.base_backend import Platform, Architecture, BinaryFormat, BackendOptions, CompilerBackend
from compiler.backend.windows_backend import WindowsBackend
from compiler.backend.linux_backend import LinuxBackend
from compiler.backend.macos_backend import MacOSBackend
from compiler.backend.playstation_backend import PlayStationBackend

def is_admin():
    """Check if the process has administrator privileges"""
    try:
        return os.name == 'nt' and ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Restart the process with administrator privileges"""
    if os.name == 'nt':  # Windows only
        script = sys.argv[0]
        params = ' '.join(sys.argv[1:])
        cmd = f'"{sys.executable}" "{script}" {params}'
        
        try:
            if not ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, cmd, None, 1):
                raise PermissionError("Failed to elevate privileges")
        except:
            raise PermissionError("Failed to run as administrator")
            
        sys.exit(0)

def parse_args():
    parser = argparse.ArgumentParser(
        description='MetaForge Compiler',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('input', help='Input file or directory')
    parser.add_argument('-o', '--output', help='Output file/directory')
    
    # Output options
    output_group = parser.add_argument_group('Output options')
    output_group.add_argument('--type', choices=['dll', 'exe', 'prx', 'self', 'pkg'], 
                            default='exe', help='Output type')
    output_group.add_argument('--name', help='Output name')
    
    # Optimization options                   
    opt_group = parser.add_argument_group('Optimization options')
    opt_group.add_argument('-O', '--optimize', choices=['0','1','2','3','s','z'],
                          default='0', help='Optimization level')
    opt_group.add_argument('--lto', action='store_true',
                          help='Enable link-time optimization')
    
    # Target options
    target_group = parser.add_argument_group('Target options')                    
    target_group.add_argument('--arch', choices=['x86','x64','arm','arm64'],
                            default='x64', help='Target architecture')
    target_group.add_argument('--platform', 
                            choices=['windows','linux','macos','playstation'],
                            default='windows', help='Target platform')
    target_group.add_argument('--cpu', help='Target CPU')
    target_group.add_argument('--features', help='CPU features')
    
    # PlayStation specific options
    ps_group = parser.add_argument_group('PlayStation options')
    ps_group.add_argument('--title-id', help='PlayStation title ID')
    ps_group.add_argument('--content-id', help='PlayStation content ID')
    ps_group.add_argument('--sdk-version', help='PlayStation SDK version')
    ps_group.add_argument('--param-sfo', help='Custom param.sfo file')
                            
    # Debug options
    debug_group = parser.add_argument_group('Debug options')
    debug_group.add_argument('-g', '--debug', action='store_true',
                           help='Generate debug information')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                           help='Verbose output')
    debug_group.add_argument('--dump-tokens', action='store_true',
                           help='Dump tokens')
    debug_group.add_argument('--dump-ast', action='store_true',
                           help='Dump AST')
    debug_group.add_argument('--dump-ir', action='store_true',
                           help='Dump IR')
                            
    return parser.parse_args()

def build_compilation_options(args) -> Dict:
    """Build compilation options"""
    platform = Platform[args.platform.upper()]
    arch = Architecture[args.arch.upper()]
    
    # Determine binary format based on platform
    binary_format = {
        Platform.WINDOWS: BinaryFormat.PE,
        Platform.LINUX: BinaryFormat.ELF,
        Platform.MACOS: BinaryFormat.MACHO,
        Platform.PLAYSTATION: BinaryFormat.ELF  # PlayStation uses modified ELF
    }[platform]
    
    # Base options
    options = {
        'output_type': args.type,
        'optimization_level': f"-O{args.optimize}",
        'debug': args.debug,
        'arch': arch,
        'platform': platform,
        'binary_format': binary_format,
        'lto': args.lto,
        'cpu': args.cpu,
        'features': args.features.split(',') if args.features else [],
        'dump_tokens': args.dump_tokens,
        'dump_ast': args.dump_ast,
        'dump_ir': args.dump_ir,
        'verbose': args.verbose
    }
    
    # Add PlayStation options if needed
    if platform == Platform.PLAYSTATION:
        options.update({
            'title_id': args.title_id or 'MFRG00001',
            'content_id': args.content_id or 'IV0000-MFRG00001_00-METAFORGEGAME01',
            'sdk_version': args.sdk_version or '5.500',
            'param_sfo': args.param_sfo
        })
        
    return options

def create_backend(options: Dict) -> CompilerBackend:
    """Create and initialize the appropriate backend"""
    platform = options['platform']
    
    backend_options = BackendOptions(
        platform=platform,
        architecture=options['arch'],
        binary_format=options['binary_format'],
        debug_info=options['debug'],
        pic=True,  # Always PIC for better compatibility
        optimize_level=int(options['optimization_level'][2]),
        target_cpu=options['cpu'],
        cpu_features=options['features']
    )
    
    logging.info(f"Creating backend for platform: {platform.value}")
    
    if platform == Platform.WINDOWS:
        logging.info("Using Windows native backend")
        return WindowsBackend(backend_options)
    elif platform == Platform.LINUX:
        logging.info("Using Linux native backend")
        return LinuxBackend(backend_options)
    elif platform == Platform.MACOS:
        logging.info("Using macOS native backend")
        return MacOSBackend(backend_options)
    elif platform == Platform.PLAYSTATION:
        logging.info("Using PlayStation native backend")
        return PlayStationBackend(backend_options)
    else:
        raise NotImplementedError(f"Platform {platform} not supported yet")

def main():
    try:
        # Parse arguments
        args = parse_args()
        
        # Setup logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('metaforge_compiler.log', mode='w')
            ]
        )
        
        logging.info("MetaForge Compiler starting...")
        logging.debug(f"Arguments: {args}")
        
        try:
            # Setup
            diagnostic = DiagnosticEmitter()
            
            # Input/output paths
            input_path = Path(args.input).resolve()
            if not input_path.exists():
                logging.error(f"Input file not found: {input_path}")
                return 1
                
            # Handle output path
            if args.output:
                output_path = Path(args.output).resolve()
                if output_path.is_dir():
                    # If it's a directory, use input filename
                    output_path = output_path / f"{input_path.stem}.exe"
            else:
                # Default output path
                output_path = input_path.with_suffix('.exe')
                
            # Build options
            options = build_compilation_options(args)
            
            # Create backend
            backend = create_backend(options)
            
            # Create compilation context
            context = CompilationContext(input_path, output_path, options)
            
            # Create and run pipeline
            pipeline = CompilationPipeline(diagnostic, backend)
            if not pipeline.compile(context):
                logging.error("Compilation failed")
                return 1
                
            logging.info(f"Successfully compiled {input_path} to {output_path}")
            return 0
            
        except Exception as e:
            logging.error(f"Compilation error: {str(e)}", exc_info=True)
            return 1
            
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())