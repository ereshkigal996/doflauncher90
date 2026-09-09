from pvf_parser import PVFParser

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

print()
print('=== 查找技能相关文件（非.act/.img）===')
skill_files = []
for item in parser.files:
    path = item['archive_path'].lower()
    if 'skill' in path and not path.endswith('.act') and not path.endswith('.img') and not path.endswith('.effect'):
        skill_files.append(item['archive_path'])

print(f'共找到 {len(skill_files)} 个')
for f in skill_files[:30]:
    print(f'  {f}')

print()
print('=== 查找包含 gunner 且大小>1000的文件 ===')
gunner_data = [item for item in parser.files if 'gunner' in item['archive_path'].lower() and item['size'] > 1000]
print(f'共找到 {len(gunner_data)} 个')
for item in gunner_data[:20]:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')

print()
print('=== 查找 Character 目录下的文件 ===')
char_files = [item for item in parser.files if 'character/' in item['archive_path'].lower()]
print(f'共找到 {len(char_files)} 个')
for item in char_files[:20]:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')
