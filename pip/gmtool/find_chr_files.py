from pvf_parser import PVFParser

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

print()
print('=== 查找路径中包含 chr 的文件 ===')
chr_files = [item for item in parser.files if 'chr' in item['archive_path'].lower()]
print(f'共找到 {len(chr_files)} 个')
for item in chr_files[:30]:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')

print()
print('=== 查找 character/gunner 目录下的非.act文件 ===')
gunner_files = [item for item in parser.files if 'character/gunner' in item['archive_path'].lower() and not item['archive_path'].endswith('.act')]
print(f'共找到 {len(gunner_files)} 个')
for item in gunner_files[:30]:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')

print()
print('=== 查找扩展名列表（前50个）===')
extensions = {}
for item in parser.files:
    path = item['archive_path']
    if '.' in path:
        ext = path.rsplit('.', 1)[-1].lower()
        extensions[ext] = extensions.get(ext, 0) + 1

sorted_exts = sorted(extensions.items(), key=lambda x: x[1], reverse=True)
for ext, count in sorted_exts[:50]:
    print(f'  .{ext}: {count} 个')
