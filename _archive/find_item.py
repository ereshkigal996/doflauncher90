import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf
import re

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()
files = parser.list_files()

target_id = '31128'
print(f'=== 查找ID: {target_id} ===')

# 查找文件名中包含该ID的文件
matched_files = []
for f in files:
    if f['name'].endswith('.stk') or f['name'].endswith('.equ'):
        file_base = f['name'].replace('.stk', '').replace('.equ', '')
        id_matches = re.findall(r'\d+', file_base)
        if id_matches and id_matches[-1] == target_id:
            matched_files.append(f)

print(f'匹配文件数: {len(matched_files)}')
for f in matched_files:
    print(f'\n文件: {f["archive_path"]}')
    item_info = extract_item_info_from_pvf(parser, f['archive_path'], f['name'])
    if item_info:
        print(f'  ID: {item_info["id"]}')
        print(f'  名称: {item_info["name"]}')
        print(f'  类型: {item_info["type"]}')
        print(f'  种类: {item_info.get("kind", "")}')
        print(f'  分类: {item_info.get("category", "")}')
    else:
        print('  提取失败')
    
    # 显示文件原始内容
    print('  --- 文件内容 ---')
    text = parser.read_file_text(f['archive_path'])
    if text:
        print(text[:600])
