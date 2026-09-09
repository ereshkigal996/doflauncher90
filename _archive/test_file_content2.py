import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()

# 读取文件内容
test_files = [
    'stackable/10000001/10000039.stk',
    'stackable/490001001/chn_490001472.stk',
]

for archive_path in test_files:
    print(f'\n=== {archive_path} ===')
    try:
        text = parser.read_file_text(archive_path)
        if text:
            print(text[:800])
        else:
            print('提取失败')
    except Exception as e:
        print(f'错误: {e}')
