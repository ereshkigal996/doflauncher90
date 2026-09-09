import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser
from gm_tool import extract_item_info_from_pvf

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()

# 测试几个特定文件
test_files = [
    'stackable/10000001/10000039.stk',
    'stackable/490001001/chn_490001472.stk',
    'stackable/10094001/10094886.stk',
    'stackable/cash/chn_490701781.stk',
    'equipment/character/common/crest/chn_2015_7th_birthday_400360010.stk',
]

print('=== 测试物品ID提取 ===')
for archive_path in test_files:
    file_name = archive_path.split('/')[-1]
    item_info = extract_item_info_from_pvf(parser, archive_path, file_name)
    if item_info:
        print(f'{file_name}')
        print(f'  ID: {item_info["id"]}')
        print(f'  名称: {item_info["name"]}')
        print(f'  类型: {item_info["type"]}')
    else:
        print(f'{file_name}: 提取失败')
