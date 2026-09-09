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
        data = parser.extract_file(archive_path)
        if data:
            # 尝试不同编码
            for encoding in ['utf-8', 'gbk', 'utf-16']:
                try:
                    text = data.decode(encoding)
                    print(f'编码: {encoding}')
                    print(text[:500])
                    break
                except:
                    continue
        else:
            print('提取失败')
    except Exception as e:
        print(f'错误: {e}')
