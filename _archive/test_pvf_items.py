# -*- coding: utf-8 -*-
"""
测试PVF解析器，读取物品中文名称
"""
import sys
import os

# 添加gmtool目录到路径
sys.path.insert(0, r"C:\Users\56518\Downloads\DBObject\pip\gmtool")

from pvf_parser import PVFParser

def parse_stk_name(content):
    """从stk文件内容中提取[name]标签的中文名称"""
    if not content:
        return None
    
    # 查找[name]标签
    name_marker = '[name]'
    idx = content.find(name_marker)
    if idx < 0:
        return None
    
    # 从[name]后开始查找反引号包裹的名称
    rest = content[idx + len(name_marker):]
    
    # 查找第一个反引号
    start = rest.find('`')
    if start < 0:
        return None
    
    # 查找结束反引号
    end = rest.find('`', start + 1)
    if end < 0:
        return None
    
    name = rest[start + 1:end]
    return name.strip()

def main():
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("=" * 70)
    print("PVF物品中文名称读取测试")
    print("=" * 70)
    print()
    
    # 1. 解析PVF
    print("[步骤1] 解析PVF文件...")
    parser = PVFParser(pvf_path)
    parser.load()
    
    print()
    summary = parser.get_summary()
    print(f"  格式: {summary['format']}")
    print(f"  文件数量: {summary['file_count']}")
    print(f"  数据块数量: {summary['group_count']}")
    
    # 2. 查找.stk文件
    print()
    print("[步骤2] 查找物品文件（.stk）...")
    stk_files = parser.find_files_by_extension('.stk')
    print(f"  找到 {len(stk_files)} 个.stk文件")
    
    # 3. 按目录分类统计
    print()
    print("[步骤3] 按目录分类统计...")
    dir_stats = {}
    for f in stk_files:
        # 获取顶层目录
        parts = f['path'].split('/')
        top_dir = parts[0] if parts else 'unknown'
        dir_stats[top_dir] = dir_stats.get(top_dir, 0) + 1
    
    sorted_dirs = sorted(dir_stats.items(), key=lambda x: x[1], reverse=True)
    print(f"  共 {len(sorted_dirs)} 个顶层目录")
    print()
    for i, (d, count) in enumerate(sorted_dirs[:15]):
        print(f"  {i+1:2d}. {d:30s} : {count:5d} 个")
    
    # 4. 读取一些物品文件的中文名称
    print()
    print("[步骤4] 读取物品中文名称（前30个）...")
    print()
    print(f"  {'序号':>4s}  {'物品ID':>10s}  {'中文名称':<40s}  {'路径'}")
    print("  " + "-" * 100)
    
    success_count = 0
    fail_count = 0
    
    for i, f in enumerate(stk_files[:30]):
        try:
            # 读取文件文本
            content = parser.read_file_text(f['archive_path'])
            
            # 提取名称
            name = parse_stk_name(content)
            
            # 从文件名提取ID
            file_id = os.path.splitext(f['name'])[0]
            # 移除chn_前缀
            if file_id.startswith('chn_'):
                file_id = file_id[4:]
            
            if name:
                print(f"  {i+1:4d}  {file_id:>10s}  {name:<40s}  {f['archive_path']}")
                success_count += 1
            else:
                print(f"  {i+1:4d}  {file_id:>10s}  {'(未找到name标签)':<40s}  {f['archive_path']}")
                fail_count += 1
                
        except Exception as e:
            print(f"  {i+1:4d}  {'错误':>10s}  {str(e)[:40]:<40s}  {f['archive_path']}")
            fail_count += 1
    
    print()
    print(f"  成功: {success_count}, 失败: {fail_count}")
    
    # 5. 搜索特定物品
    print()
    print("[步骤5] 搜索特定物品（消耗品、装备等）...")
    
    # 查找stackable目录下的物品
    stackable_files = [f for f in stk_files if 'stackable' in f['path'].lower()]
    print(f"  stackable目录下物品: {len(stackable_files)} 个")
    
    # 读取前10个消耗品
    print()
    print("  消耗品示例（前10个）:")
    print(f"  {'序号':>4s}  {'物品ID':>10s}  {'中文名称':<40s}")
    print("  " + "-" * 70)
    
    for i, f in enumerate(stackable_files[:10]):
        try:
            content = parser.read_file_text(f['archive_path'])
            name = parse_stk_name(content)
            file_id = os.path.splitext(f['name'])[0]
            if file_id.startswith('chn_'):
                file_id = file_id[4:]
            
            if name:
                print(f"  {i+1:4d}  {file_id:>10s}  {name:<40s}")
            else:
                print(f"  {i+1:4d}  {file_id:>10s}  (未找到名称)")
        except Exception as e:
            print(f"  {i+1:4d}  错误: {str(e)[:30]}")
    
    # 6. 保存所有物品名称到JSON
    print()
    print("[步骤6] 保存所有物品名称到JSON...")
    
    import json
    items_list = []
    
    for f in stk_files:
        try:
            content = parser.read_file_text(f['archive_path'])
            name = parse_stk_name(content)
            file_id = os.path.splitext(f['name'])[0]
            if file_id.startswith('chn_'):
                file_id = file_id[4:]
            
            try:
                item_id = int(file_id)
            except:
                item_id = file_id
            
            items_list.append({
                'id': item_id,
                'name': name if name else '',
                'path': f['archive_path'],
            })
        except:
            pass
    
    output_path = r"C:\Users\56518\Downloads\DBObject\pvf_items_test.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(items_list, f, ensure_ascii=False, indent=2)
    
    print(f"  已保存 {len(items_list)} 个物品到: {output_path}")
    print(f"  文件大小: {os.path.getsize(output_path) / 1024:.1f} KB")
    
    # 统计有名称的物品
    named_items = [item for item in items_list if item['name']]
    print(f"  有中文名称的物品: {len(named_items)} 个")
    print(f"  无名称的物品: {len(items_list) - len(named_items)} 个")
    
    print()
    print("=" * 70)
    print("测试完成！")
    print("=" * 70)

if __name__ == '__main__':
    main()
