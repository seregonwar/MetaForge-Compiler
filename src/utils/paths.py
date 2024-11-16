import os
from pathlib import Path

class VSPaths:
    def __init__(self):
        self.sdk_path = Path(r"C:\Program Files (x86)\Windows Kits\10")
        self.vs_path = Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community")
        
        # Find latest installed SDK version
        sdk_versions = [x for x in (self.sdk_path / "Include").iterdir() if x.is_dir()]
        self.sdk_version = str(sorted(sdk_versions)[-1].name)
        
        # Find latest installed VS version
        vs_versions = [x for x in (self.vs_path / "VC" / "Tools" / "MSVC").iterdir() if x.is_dir()]
        self.vs_version = str(sorted(vs_versions)[-1].name)

    @property 
    def include_paths(self):
        sdk_include = self.sdk_path / "Include" / self.sdk_version
        vs_include = self.vs_path / "VC" / "Tools" / "MSVC" / self.vs_version / "include"
        
        return [
            str(vs_include),
            str(sdk_include / "ucrt"),
            str(sdk_include / "shared"),
            str(sdk_include / "um"),
            str(sdk_include / "km"),
            str(sdk_include / "wdf")
        ]

    @property
    def lib_paths(self):
        sdk_lib = self.sdk_path / "Lib" / self.sdk_version
        vs_lib = self.vs_path / "VC" / "Tools" / "MSVC" / self.vs_version / "lib" / "x64"
        
        return [
            str(vs_lib),
            str(sdk_lib / "ucrt" / "x64"),
            str(sdk_lib / "um" / "x64"), 
            str(sdk_lib / "km" / "x64")
        ]

    def get_vcvars_path(self):
        return str(self.vs_path / "VC" / "Auxiliary" / "Build" / "vcvars64.bat")