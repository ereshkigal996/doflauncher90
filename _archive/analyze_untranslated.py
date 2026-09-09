# -*- coding: utf-8 -*-
"""
分析PVF中实际出现的物品类型和来源，对比翻译映射表，找出未翻译的项
"""
import sys
import os
import struct
from collections import Counter

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser

# 导入翻译映射表
from gm_tool import EQUIP_TYPE_MAP, KIND_MAP, SOURCE_MAP

def analyze_item_types(parser):
    """分析所有物品文件中的类型标签"""
    print("=" * 70)
    print("分析物品类型标签")
    print("=" * 70)
    print()
    
    # 查找所有.stk和.equ文件
    stk_files = parser.find_files_by_extension('.stk')
    equ_files = parser.find_files_by_extension('.equ')
    
    print(f".stk文件: {len(stk_files)} 个")
    print(f".equ文件: {len(equ_files)} 个")
    print()
    
    # 统计出现的类型标签
    type_counter = Counter()
    stackable_type_counter = Counter()
    attach_type_counter = Counter()
    
    all_files = stk_files + equ_files
    total = len(all_files)
    
    for idx, file_info in enumerate(all_files):
        if idx % 5000 == 0:
            print(f"  处理进度: {idx}/{total}")
        
        archive_path = file_info['archive_path']
        raw = parser.read_file_raw(archive_path)
        if not raw or len(raw) < 5:
            continue
        
        line_count = len(raw) // 5
        current_tag = None
        
        for i in range(line_count):
            off = i * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                text = parser._resolve_string(value)
                if text:
                    current_tag = text.strip('[]')
                    
                    # 统计常见标签
                    if text in ['[stackable type]', '[equipment type]', '[attach type]', '[type]']:
                        pass
                        
            elif token_type == 6 and current_tag:
                text = parser._resolve_string(value)
                if text:
                    if current_tag == 'stackable type':
                        stackable_type_counter[text] += 1
                    elif current_tag == 'equipment type':
                        type_counter[text] += 1
                    elif current_tag == 'attach type':
                        attach_type_counter[text] += 1
                current_tag = None
    
    print()
    print("=" * 70)
    print("统计结果")
    print("=" * 70)
    
    # 装备类型
    print()
    print("【装备类型 equipment type】")
    print(f"  共出现 {len(type_counter)} 种")
    print()
    print("  已翻译:")
    translated_equip = set()
    for t, count in type_counter.most_common():
        if t in EQUIP_TYPE_MAP:
            print(f"    ✓ {t:<30s} -> {EQUIP_TYPE_MAP[t]:<15s} ({count}次)")
            translated_equip.add(t)
    
    print()
    print("  未翻译:")
    untranslated_equip = []
    for t, count in type_counter.most_common():
        if t not in EQUIP_TYPE_MAP:
            print(f"    ✗ {t:<30s} ({count}次)")
            untranslated_equip.append((t, count))
    
    # 消耗品类型
    print()
    print("【消耗品类型 stackable type】")
    print(f"  共出现 {len(stackable_type_counter)} 种")
    print()
    print("  已翻译:")
    translated_stack = set()
    for t, count in stackable_type_counter.most_common():
        if t in KIND_MAP or t in EQUIP_TYPE_MAP:
            trans = KIND_MAP.get(t, EQUIP_TYPE_MAP.get(t, t))
            print(f"    ✓ {t:<30s} -> {trans:<15s} ({count}次)")
            translated_stack.add(t)
    
    print()
    print("  未翻译 (前30个):")
    untranslated_stack = []
    for t, count in stackable_type_counter.most_common(30):
        if t not in KIND_MAP and t not in EQUIP_TYPE_MAP:
            print(f"    ✗ {t:<30s} ({count}次)")
            untranslated_stack.append((t, count))
    
    # 附加类型
    print()
    print("【附加类型 attach type】")
    print(f"  共出现 {len(attach_type_counter)} 种")
    print()
    for t, count in attach_type_counter.most_common(20):
        print(f"    {t:<30s} ({count}次)")
    
    # 总结
    print()
    print("=" * 70)
    print("未翻译项总结")
    print("=" * 70)
    print()
    print(f"装备类型未翻译: {len(untranslated_equip)} 种")
    print(f"消耗品类型未翻译: {len(untranslated_stack)} 种 (仅显示前30)")
    print()
    
    # 输出建议添加的翻译
    print("建议添加到EQUIP_TYPE_MAP的翻译:")
    for t, count in untranslated_equip[:20]:
        print(f"    '{t}': '',  # ({count}次)")
    
    print()
    print("建议添加到KIND_MAP的翻译 (消耗品类型):")
    for t, count in untranslated_stack[:20]:
        print(f"    '{t}': '',  # ({count}次)")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("加载PVF解析器...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print(f"PVF加载成功！")
    print(f"  strA大小: {len(parser.str_a) if parser.str_a else 0}")
    print(f"  strW大小: {len(parser.str_w) if parser.str_w else 0}")
    print()
    
    analyze_item_types(parser)
    
    print()
    print("分析完成！")

if __name__ == '__main__':
    main()
