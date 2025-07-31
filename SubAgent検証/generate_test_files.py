#!/usr/bin/env python3
"""
Sub-Agent検証用テストファイル生成スクリプト
様々なサイズ・複雑度のファイルを生成
"""

import os
import random


def generate_simple_code(lines):
    """単純なPythonコード生成"""
    code = []
    for i in range(lines):
        if i % 10 == 0:
            code.append(f"\n# Section {i//10}")
        code.append(f"variable_{i} = {random.randint(1, 100)}")
    return "\n".join(code)


def generate_complex_code(lines):
    """複雑な相互依存コード生成"""
    code = [
        "import os",
        "import sys",
        "import json",
        "from datetime import datetime",
        "from typing import List, Dict, Optional",
        "",
        "class ComplexSystem:",
        "    def __init__(self):",
        "        self.data = {}",
    ]

    for i in range(lines - len(code)):
        if i % 20 == 0:
            code.append(f"\n    def method_{i}(self, param_{i}: int) -> Dict:")
            code.append(f"        # Complex logic section {i}")
        code.append(f"        result_{i} = self.process_data({random.randint(1, 100)})")

    return "\n".join(code)


def create_test_files():
    """テストファイル群の生成"""
    base_dir = "test_files"

    # 極小ファイル (1-10行)
    with open(f"{base_dir}/minimal/tiny.py", "w") as f:
        f.write(generate_simple_code(5))

    with open(f"{base_dir}/minimal/mini.py", "w") as f:
        f.write(generate_simple_code(10))

    # 小ファイル (50-100行)
    with open(f"{base_dir}/small/small_simple.py", "w") as f:
        f.write(generate_simple_code(50))

    with open(f"{base_dir}/small/small_complex.py", "w") as f:
        f.write(generate_complex_code(100))

    # 中ファイル (500-1000行)
    with open(f"{base_dir}/medium/medium_simple.py", "w") as f:
        f.write(generate_simple_code(500))

    with open(f"{base_dir}/medium/medium_complex.py", "w") as f:
        f.write(generate_complex_code(1000))

    # 大ファイル (5000+行)
    print("大ファイル生成中...")
    with open(f"{base_dir}/large/large_simple.py", "w") as f:
        f.write(generate_simple_code(5000))

    with open(f"{base_dir}/large/large_complex.py", "w") as f:
        f.write(generate_complex_code(10000))

    # マルチファイルプロジェクト
    for i in range(5):
        with open(f"{base_dir}/small/module_{i}.py", "w") as f:
            f.write(f"# Module {i}\n" + generate_simple_code(30))

    for i in range(20):
        with open(f"{base_dir}/medium/component_{i}.py", "w") as f:
            f.write(f"# Component {i}\n" + generate_complex_code(200))

    print("テストファイル生成完了")

    # ファイルサイズ確認
    for root, _dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                size = os.path.getsize(path)
                lines = sum(1 for line in open(path))
                print(f"{path}: {lines}行, {size/1024:.1f}KB")


if __name__ == "__main__":
    create_test_files()
