from pvf_parser import PVFParser

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

# 读取神枪手的.chr文件
chr_path = 'character/gunner/gunner.chr'
print(f'\n=== 读取 {chr_path} ===')

try:
    # 尝试读取文本内容
    text = parser.read_file_text(chr_path)
    if text:
        print(f'文本内容长度: {len(text)}')
        print(f'\n前2000字符:')
        print(text[:2000])
    else:
        print('read_file_text返回空，尝试read_file_raw...')
        data = parser.read_file_raw(chr_path)
        if data:
            print(f'原始数据长度: {len(data)}')
            print(f'\n前500字节十六进制:')
            print(data[:500].hex())
            print(f'\n尝试解码为文本:')
            try:
                print(data[:1000].decode('utf-8', errors='replace'))
            except:
                print('无法解码')
except Exception as e:
    print(f'读取失败: {e}')
    import traceback
    traceback.print_exc()
