from pvf_parser import PVFParser
import struct

pvf_path = r'C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf'
print('正在加载PVF...')
parser = PVFParser(pvf_path)
parser.load()

# 查找神枪手的.chr文件
chr_path = 'character/gunner/gunner.chr'
print(f'\n=== 读取 {chr_path} ===')

# 查找文件索引
file_index = None
for item in parser.files:
    if item['archive_path'].lower() == chr_path.lower():
        file_index = item['index']
        print(f'找到文件，index={file_index}, size={item["size"]} bytes')
        break

if file_index is not None:
    # 尝试提取文件内容
    try:
        # 查看PVFParser有没有提取文件的方法
        methods = [m for m in dir(parser) if not m.startswith('_')]
        print(f'PVFParser方法: {methods}')
        
        # 尝试调用 extract 或 get_file 方法
        if hasattr(parser, 'extract_file'):
            data = parser.extract_file(file_index)
        elif hasattr(parser, 'get_file'):
            data = parser.get_file(file_index)
        elif hasattr(parser, 'read_file'):
            data = parser.read_file(file_index)
        else:
            print('没有找到提取文件的方法，尝试直接读取...')
            # 查看文件数据结构
            print(f'files[{file_index}] = {parser.files[file_index]}')
            data = None
        
        if data:
            print(f'\n文件内容（前200字节十六进制）:')
            print(data[:200].hex())
            
            print(f'\n文件内容（前200字节文本）:')
            try:
                print(data[:200].decode('utf-8', errors='replace'))
            except:
                print('无法解码为文本')
                
            # 尝试解析为文本
            print(f'\n尝试查找技能ID...')
            # 搜索可能的技能ID模式
            text = data.decode('utf-8', errors='ignore')
            # 查找包含 skill 或 awaken 的行
            for i, line in enumerate(text.split('\n')[:50]):
                if line.strip():
                    print(f'  行{i}: {line.strip()[:100]}')
    except Exception as e:
        print(f'提取文件失败: {e}')
        import traceback
        traceback.print_exc()
