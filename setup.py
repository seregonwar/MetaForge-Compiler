# MetaForge Compiler - Setup
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
# Module: Setup
# Author: SeregonWar (https://github.com/SeregonWar)
# License: MIT License
#
# Description:
# Source code for the creation of the MetaForge compiler packages.
#
# Key Features:
# - Creation of a package for the installation of the compiler.
# - Configuration of the dependencies.
#
# Usage & Extensibility:
# This file should not be modified for normal use.
# To create a package, run "python setup.py sdist bdist_wheel".
# To install the package, run "pip install dist/metaforge-<version>-py3-none-any.whl".

setup(
    name="metaforge",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'metaforge=src.compiler.main:main',
        ],
    },
)
