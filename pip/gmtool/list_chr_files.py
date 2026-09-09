from pvf_parser import PVFParser

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

print()
print('=== 所有.chr文件 ===')
chr_files = [item for item in parser.files if item['archive_path'].lower().endswith('.chr')]
print(f'共找到 {len(chr_files)} 个')
for item in chr_files:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')

print()
print('=== 所有.skl文件（前30个）===')
skl_files = [item for item in parser.files if item['archive_path'].lower().endswith('.skl')]
print(f'共找到 {len(skl_files)} 个')
for item in skl_files[:30]:
    print(f'  {item["archive_path"]} ({item["size"]} bytes)')
