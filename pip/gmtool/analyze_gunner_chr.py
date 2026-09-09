from pvf_parser import PVFParser

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

# 读取神枪手的.chr文件
chr_path = 'character/gunner/gunner.chr'
print(f'\n=== 读取 {chr_path} ===')

text = parser.read_file_text(chr_path)
print(f'文本长度: {len(text)}')

# 查找 [awakening name] 部分
if '[awakening name]' in text:
    idx = text.index('[awakening name]')
    print(f'\n=== [awakening name] 部分（前3000字符）===')
    print(text[idx:idx+3000])
else:
    print('没有找到 [awakening name]')
    
    # 查找所有包含 awakening 的行
    print('\n=== 包含 awakening 的行 ===')
    for i, line in enumerate(text.split('\n')):
        if 'awakening' in line.lower():
            print(f'  行{i}: {line.strip()}')

# 查找所有 [showskill level] 的位置
print('\n=== [showskill level] 的位置 ===')
import re
for match in re.finditer(r'\[showskill level\]\s*(\d+)', text):
    level = match.group(1)
    start = match.start()
    # 显示前后200字符
    context = text[max(0, start-100):start+300]
    print(f'\n位置 {start}, level={level}:')
    print(context)
    print('---')
