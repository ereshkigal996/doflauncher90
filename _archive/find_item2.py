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

matched_files = []
for f in files:
    if f['name'].endswith('.stk') or f['name'].endswith('.equ'):
        file_base = f['name'].replace('.stk', '').replace('.equ', '')
        id_matches = re.findall(r'\d+', file_base)
        if id_matches and id_matches[-1] == target_id:
            matched_files.append(f)

print(f'匹配文件数: {len(matched_files)}')
for f in matched_files:
    archive_path = f['archive_path']
    file_name = f['name']
    print(f'\n文件: {archive_path}')
    item_info = extract_item_info_from_pvf(parser, archive_path, file_name)
    if item_info:
        print(f'  ID: {item_info["id"]}')
        print(f'  名称: {item_info["name"]}')
        print(f'  类型: {item_info["type"]}')
        print(f'  种类: {item_info.get("kind", "")}')
        print(f'  分类: {item_info.get("category", "")}')
    else:
        print('  提取失败')
