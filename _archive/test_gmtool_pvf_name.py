# -*- coding: utf-8 -*-
"""
测试GM工具从PVF解析物品名称的功能
"""
import sys
import os

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")

# 导入GM工具中的函数
from gm_tool import extract_item_name_from_pvf, load_pvf_parser

def main():
    print("测试从PVF解析物品名称")
    print("=" * 60)
    
    # 加载PVF解析器
    print("\n加载PVF解析器...")
    parser = load_pvf_parser()
    if not parser:
        print("PVF解析器加载失败！")
        return
    
    print(f"PVF解析器加载成功！")
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    
    # 测试物品
    test_items = [
        ("神圣稀有克隆装扮礼盒", "stackable/cash/chn_20140729_randombox/chn_clone_rare_avatarbox_2683816.stk"),
        ("引用格式物品", "stackable/10000001/10000059.stk"),
    ]
    
    print("\n" + "=" * 60)
    print("测试物品名称解析")
    print("=" * 60)
    
    for name, path in test_items:
        print(f"\n[{name}]")
        print(f"  路径: {path}")
        result = extract_item_name_from_pvf(parser, path)
        print(f"  解析结果: '{result}'")
    
    # 测试更多物品
    print("\n" + "=" * 60)
    print("测试前20个.stk物品")
    print("=" * 60)
    
    stk_files = parser.find_files_by_extension('.stk')
    success = 0
    fail = 0
    
    for i, f in enumerate(stk_files[:20]):
        name = extract_item_name_from_pvf(parser, f['archive_path'])
        if name and not name.startswith('name_'):
            success += 1
            print(f"  [{i+1:2d}] ✓ {f['name']:<30s} -> {name[:40]}")
        else:
            fail += 1
            print(f"  [{i+1:2d}] ✗ {f['name']:<30s} -> {name if name else '(空)'}")
    
    print(f"\n统计: 成功 {success}, 失败 {fail}, 成功率 {success/20*100:.1f}%")
    
    print("\n测试完成！")

if __name__ == '__main__':
    main()
