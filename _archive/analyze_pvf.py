import sys
sys.path.insert(0, r'C:\Users\56518\Downloads\DBObject\pip\gmtool')
from pvf_parser import PVFParser

parser = PVFParser(r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf')
parser.load()
files = parser.list_files()

# 使用archive_path字段
stackable_files = [f for f in files if 'stackable' in f['archive_path'].lower() and f['archive_path'].endswith('.stk')]
print(f'总stk文件数: {len(stackable_files)}')

# 统计纯数字文件名
pure_numeric = [f for f in stackable_files if f['name'].replace('.stk', '').isdigit()]
print(f'纯数字文件名: {len(pure_numeric)}')

# 统计带前缀的文件名
with_prefix = [f for f in stackable_files if not f['name'].replace('.stk', '').isdigit()]
print(f'带前缀文件名: {len(with_prefix)}')

# 显示一些带前缀的文件名示例
print('\n带前缀文件名示例（前30个）:')
for f in with_prefix[:30]:
    print(f'  {f["name"]}')

# 统计前缀类型
prefixes = set()
for f in with_prefix:
    filename = f['name'].replace('.stk', '')
    if '_' in filename:
        prefix = filename.split('_')[0]
        prefixes.add(prefix)
print(f'\n前缀类型: {sorted(prefixes)}')

# 检查ID=1的文件
print('\n文件名以1开头的文件（前10个）:')
id1_files = [f for f in stackable_files if f['name'].startswith('1')]
for f in id1_files[:10]:
    print(f'  {f["name"]}')
