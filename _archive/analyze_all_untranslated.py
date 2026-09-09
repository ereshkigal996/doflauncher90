# -*- coding: utf-8 -*-
"""
全面分析所有未翻译的物品类型
"""
import sys
import os
import struct
from collections import Counter, defaultdict

sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")
from pvf_parser import PVFParser
from gm_tool import (
    EQUIP_TYPE_MAP, KIND_MAP, STACKABLE_TYPE_MAP, ATTACH_TYPE_MAP,
    extract_item_name_from_pvf
)

def analyze_all_untranslated(parser):
    """全面分析所有未翻译的物品类型"""
    print("=" * 80)
    print("全面分析所有未翻译的物品类型")
    print("=" * 80)
    print()
    
    # 查找所有.stk和.equ文件
    stk_files = parser.find_files_by_extension('.stk')
    equ_files = parser.find_files_by_extension('.equ')
    all_files = stk_files + equ_files
    
    print(f".stk文件: {len(stk_files)} 个")
    print(f".equ文件: {len(equ_files)} 个")
    print(f"总计: {len(all_files)} 个")
    print()
    
    # 统计各种类型
    equip_type_counter = Counter()
    stackable_type_counter = Counter()
    attach_type_counter = Counter()
    kind_counter = Counter()
    
    # 保存每种类型的示例物品
    equip_type_examples = defaultdict(list)
    stackable_type_examples = defaultdict(list)
    attach_type_examples = defaultdict(list)
    
    total = len(all_files)
    
    for idx, file_info in enumerate(all_files):
        if idx % 20000 == 0:
            print(f"  扫描进度: {idx}/{total}")
        
        archive_path = file_info['archive_path']
        raw = parser.read_file_raw(archive_path)
        if not raw or len(raw) < 5:
            continue
        
        line_count = len(raw) // 5
        current_tag = None
        item_name = None
        
        for i in range(line_count):
            off = i * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            
            if token_type == 3:
                text = parser._resolve_string(value)
                if text:
                    current_tag = text.strip('[]')
                    
            elif token_type == 6 and current_tag:
                text = parser._resolve_string(value)
                if text:
                    if current_tag == 'equipment type':
                        equip_type_counter[text] += 1
                        if len(equip_type_examples[text]) < 3:
                            if not item_name:
                                item_name = extract_item_name_from_pvf(parser, archive_path)
                            equip_type_examples[text].append({
                                'name': item_name if item_name else '(未命名)',
                                'path': archive_path
                            })
                    elif current_tag == 'stackable type':
                        stackable_type_counter[text] += 1
                        if len(stackable_type_examples[text]) < 3:
                            if not item_name:
                                item_name = extract_item_name_from_pvf(parser, archive_path)
                            stackable_type_examples[text].append({
                                'name': item_name if item_name else '(未命名)',
                                'path': archive_path
                            })
                    elif current_tag == 'attach type':
                        attach_type_counter[text] += 1
                        if len(attach_type_examples[text]) < 3:
                            if not item_name:
                                item_name = extract_item_name_from_pvf(parser, archive_path)
                            attach_type_examples[text].append({
                                'name': item_name if item_name else '(未命名)',
                                'path': archive_path
                            })
                current_tag = None
    
    print()
    print("=" * 80)
    print("统计结果")
    print("=" * 80)
    
    # 装备类型
    print()
    print("【装备类型 equipment type】")
    print(f"  共出现 {len(equip_type_counter)} 种")
    print()
    
    translated_equip = set(EQUIP_TYPE_MAP.keys())
    untranslated_equip = []
    
    print("  已翻译:")
    for t, count in equip_type_counter.most_common():
        if t in translated_equip:
            print(f"    ✓ {t:<30s} -> {EQUIP_TYPE_MAP[t]:<15s} ({count}次)")
        else:
            untranslated_equip.append((t, count))
    
    print()
    print("  未翻译:")
    for t, count in untranslated_equip:
        print(f"    ✗ {t:<30s} ({count}次)")
        for ex in equip_type_examples[t][:2]:
            print(f"        示例: {ex['name']}")
    
    # 消耗品类型
    print()
    print("【消耗品类型 stackable type】")
    print(f"  共出现 {len(stackable_type_counter)} 种")
    print()
    
    translated_stack = set(STACKABLE_TYPE_MAP.keys())
    untranslated_stack = []
    
    print("  已翻译:")
    for t, count in stackable_type_counter.most_common():
        if t in translated_stack:
            print(f"    ✓ {t:<35s} -> {STACKABLE_TYPE_MAP[t]:<15s} ({count}次)")
        else:
            untranslated_stack.append((t, count))
    
    print()
    print("  未翻译 (按出现次数排序):")
    for i, (t, count) in enumerate(untranslated_stack):
        print(f"    [{i+1:2d}] ✗ {t:<35s} ({count}次)")
        for ex in stackable_type_examples[t][:1]:
            print(f"          示例: {ex['name']}")
    
    # 附加类型
    print()
    print("【附加类型 attach type】")
    print(f"  共出现 {len(attach_type_counter)} 种")
    print()
    
    translated_attach = set(ATTACH_TYPE_MAP.keys())
    untranslated_attach = []
    
    print("  已翻译:")
    for t, count in attach_type_counter.most_common():
        if t in translated_attach:
            print(f"    ✓ {t:<25s} -> {ATTACH_TYPE_MAP[t]:<15s} ({count}次)")
        else:
            untranslated_attach.append((t, count))
    
    print()
    print("  未翻译:")
    for t, count in untranslated_attach:
        print(f"    ✗ {t:<25s} ({count}次)")
        for ex in attach_type_examples[t][:2]:
            print(f"        示例: {ex['name']}")
    
    # 总结
    print()
    print("=" * 80)
    print("未翻译项总结")
    print("=" * 80)
    print()
    print(f"  装备类型未翻译: {len(untranslated_equip)} 种")
    print(f"  消耗品类型未翻译: {len(untranslated_stack)} 种")
    print(f"  附加类型未翻译: {len(untranslated_attach)} 种")
    print(f"  总计未翻译: {len(untranslated_equip) + len(untranslated_stack) + len(untranslated_attach)} 种")
    print()
    
    # 输出建议添加的翻译（高频）
    print("建议添加的高频翻译（出现>10次）:")
    print()
    for t, count in untranslated_stack:
        if count > 10:
            print(f"    '{t}': '',  # ({count}次)")

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("加载PVF解析器...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print(f"PVF加载成功！")
    print()
    
    analyze_all_untranslated(parser)
    
    print()
    print("分析完成！")

if __name__ == '__main__':
    main()
