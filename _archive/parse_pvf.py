# -*- coding: utf-8 -*-
"""
使用Zageku/DNF_pvf_python的PVF解析器解析服务端PVF文件
"""
import sys
import os
import time
import json

# 添加项目路径
project_path = r"C:\Users\56518\Downloads\DBObject\DNF_pvf_python"
sys.path.insert(0, project_path)

# PVF文件路径
pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"

print("=" * 60)
print("PVF文件解析工具")
print("=" * 60)
print(f"项目路径: {project_path}")
print(f"PVF文件: {pvf_path}")
print(f"文件大小: {os.path.getsize(pvf_path) / 1024 / 1024:.2f} MB")
print()

try:
    # 导入PVF解析器
    print("[1/5] 导入PVF解析器...")
    from dnfpkgtool.pvfReader import PVFHeader, TinyPVF, StringTable
    print("  ✓ PVF解析器导入成功")
    print()
    
    # 解析PVF文件头
    print("[2/5] 解析PVF文件头...")
    start_time = time.time()
    header = PVFHeader(pvf_path, readFullFile=False)
    elapsed = time.time() - start_time
    print(f"  ✓ 文件头解析完成 (耗时: {elapsed:.2f}秒)")
    print(f"  - UUID长度: {header.uuid_len}")
    print(f"  - UUID: {header.uuid[:36]}")
    print(f"  - PVF版本: {header.PVFversion}")
    print(f"  - 文件树长度: {header.dirTreeLength}")
    print(f"  - 文件树CRC32: {hex(header.dirTreeCrc32)}")
    print(f"  - 文件数量: {header.numFilesInDirTree}")
    print(f"  - 文件头长度: {header.headerLength}")
    print()
    
    # 加载文件树
    print("[3/5] 加载文件树...")
    start_time = time.time()
    tiny_pvf = TinyPVF(header, encode='big5')
    tiny_pvf.load_Leafs(structured=True)
    elapsed = time.time() - start_time
    print(f"  ✓ 文件树加载完成 (耗时: {elapsed:.2f}秒)")
    print(f"  - 解析文件数: {len(tiny_pvf.fileTreeDict)}")
    print()
    
    # 统计文件类型
    print("[4/5] 统计文件类型...")
    file_extensions = {}
    file_dirs = {}
    for file_path in tiny_pvf.fileTreeDict.keys():
        # 统计扩展名
        ext = os.path.splitext(file_path)[1].lower()
        file_extensions[ext] = file_extensions.get(ext, 0) + 1
        
        # 统计目录
        dir_name = os.path.dirname(file_path)
        top_dir = dir_name.split('/')[0] if '/' in dir_name else dir_name
        file_dirs[top_dir] = file_dirs.get(top_dir, 0) + 1
    
    print("  ✓ 文件类型统计完成")
    print()
    
    # 输出结果
    print("[5/5] 输出解析结果...")
    print()
    print("=" * 60)
    print("一、PVF文件基本信息")
    print("=" * 60)
    print(f"文件路径: {pvf_path}")
    print(f"文件大小: {os.path.getsize(pvf_path) / 1024 / 1024:.2f} MB")
    print(f"PVF版本: {header.PVFversion}")
    print(f"文件数量: {header.numFilesInDirTree}")
    print(f"UUID: {header.uuid[:36].decode('ascii', errors='replace')}")
    print()
    
    print("=" * 60)
    print("二、文件扩展名统计 (前20)")
    print("=" * 60)
    sorted_exts = sorted(file_extensions.items(), key=lambda x: x[1], reverse=True)
    for i, (ext, count) in enumerate(sorted_exts[:20]):
        print(f"  {i+1:2d}. {ext:10s} : {count:6d} 个文件")
    print()
    
    print("=" * 60)
    print("三、顶层目录统计 (前20)")
    print("=" * 60)
    sorted_dirs = sorted(file_dirs.items(), key=lambda x: x[1], reverse=True)
    for i, (dir_name, count) in enumerate(sorted_dirs[:20]):
        print(f"  {i+1:2d}. {dir_name:30s} : {count:6d} 个文件")
    print()
    
    print("=" * 60)
    print("四、部分文件列表 (前50)")
    print("=" * 60)
    for i, file_path in enumerate(list(tiny_pvf.fileTreeDict.keys())[:50]):
        leaf = tiny_pvf.fileTreeDict[file_path]
        size_kb = leaf['fileLength'] / 1024
        print(f"  {i+1:3d}. [{size_kb:8.2f} KB] {file_path}")
    print()
    
    # 保存解析结果到JSON
    output_path = r"C:\Users\56518\Downloads\DBObject\pvf_parse_result.json"
    result = {
        "pvf_info": {
            "path": pvf_path,
            "size_mb": round(os.path.getsize(pvf_path) / 1024 / 1024, 2),
            "version": header.PVFversion,
            "file_count": header.numFilesInDirTree,
            "uuid": header.uuid[:36].decode('ascii', errors='replace'),
            "dir_tree_length": header.dirTreeLength,
            "dir_tree_crc32": hex(header.dirTreeCrc32)
        },
        "file_extensions": dict(sorted_exts),
        "top_dirs": dict(sorted_dirs),
        "file_list": list(tiny_pvf.fileTreeDict.keys())[:1000]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 解析结果已保存到: {output_path}")
    print()
    print("=" * 60)
    print("解析完成！")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ 解析失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
