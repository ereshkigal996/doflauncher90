import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()
files = parser.list_files()

# 查找一些常见物品
test_ids = ['1', '490001472', '10094886', '490701781', '2682988']

print("=== 测试物品ID和名称 ===")
for test_id in test_ids:
    print(f"\n查找ID: {test_id}")
    # 查找文件名包含该ID的文件
    matched_files = [f for f in files if test_id in f['name'] and f['name'].endswith('.stk')]
    print(f"  匹配文件数: {len(matched_files)}")
    for f in matched_files[:5]:
        print(f"  - {f['archive_path']}")
        # 提取物品信息
        item_info = extract_item_info_from_pvf(parser, f['archive_path'], f['name'])
        if item_info:
            print(f"    提取ID: {item_info['id']}")
            print(f"    提取名称: {item_info['name']}")
            print(f"    提取类型: {item_info['type']}")
        else:
            print(f"    提取失败")

# 统计物品ID格式
print("\n=== 统计物品ID格式 ===")
stackable_files = [f for f in files if 'stackable' in f['archive_path'].lower() and f['archive_path'].endswith('.stk')]
print(f"总stk文件数: {len(stackable_files)}")

pure_numeric = 0
chn_prefix = 0
other_prefix = 0
for f in stackable_files[:1000]:  # 只统计前1000个
    file_base = f['name'].replace('.stk', '')
    if file_base.isdigit():
        pure_numeric += 1
    elif file_base.startswith('chn_'):
        chn_prefix += 1
    else:
        other_prefix += 1

print(f"纯数字: {pure_numeric}")
print(f"chn_前缀: {chn_prefix}")
print(f"其他前缀: {other_prefix}")
