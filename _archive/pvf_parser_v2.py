# -*- coding: utf-8 -*-
"""
DNF 90版本 PVF文件解析器（基于服务端Go源码重写）
支持 NKPI 和 ProtectedNKPI 两种格式
"""
import struct
import zlib
import os
import json
from pathlib import Path

# 常量
HEADER_SIZE = 0x30       # 文件头大小 48字节
FILE_ITEM_SIZE = 0x18    # 文件表条目大小 24字节
GROUP_ITEM_SIZE = 8      # 分组表条目大小 8字节
MAGIC_SIGNATURE = 0x69706B6E  # "nkpi" 小端序


class PVFParser:
    """DNF PVF文件解析器"""
    
    def __init__(self, pvf_path):
        self.pvf_path = pvf_path
        self.data = None
        self.format = None  # "nkpi" 或 "protected_nkpi"
        self.file_count = 0
        self.body_size = 0
        self.group_count = 0
        self.hash_size = 0
        self.name_size = 0
        self.body_off = 0
        self.files = []
        self.items = []
        self.groups = []
        self.str_a = None  # UTF-8字符串池
        self.str_w = None  # UTF-16字符串池
        self.path_idx = {}
        self.chunks = {}
        
    def load(self):
        """加载并解析PVF文件"""
        print(f"[1/6] 读取PVF文件: {self.pvf_path}")
        with open(self.pvf_path, 'rb') as f:
            self.data = f.read()
        print(f"  文件大小: {len(self.data)} 字节 ({len(self.data)/1024/1024:.2f} MB)")
        
        print("[2/6] 解析文件头...")
        if not self._parse_header():
            raise Exception("无法解析PVF文件头，可能不是有效的NKPI格式")
        
        print(f"  格式: {self.format}")
        print(f"  文件数量: {self.file_count}")
        print(f"  分组数量: {self.group_count}")
        print(f"  主体大小: {self.body_size}")
        
        print("[3/6] 解析字符串池...")
        self._parse_string_pool()
        
        print("[4/6] 解析分组表...")
        self._parse_groups()
        
        print("[5/6] 解析文件表...")
        self._parse_files()
        
        print("[6/6] 解析完成！")
        return True
    
    def _parse_header(self):
        """解析文件头，尝试NKPI和ProtectedNKPI两种格式"""
        if len(self.data) < HEADER_SIZE:
            return False
        
        # 尝试NKPI格式
        header = bytearray(self.data[:HEADER_SIZE])
        self._decrypt_guard(header)
        self._decrypt("HeaD", header, 0x269EC3)
        
        magic = struct.unpack('<I', header[0:4])[0]
        if magic == MAGIC_SIGNATURE:
            self.format = "nkpi"
            self._parse_header_sizes(header)
            return True
        
        # 尝试ProtectedNKPI格式
        header = bytearray(self.data[:HEADER_SIZE])
        self._decrypt_protected("hEAd", header, 0x269EC3)
        
        magic = struct.unpack('<I', header[0:4])[0]
        if magic == MAGIC_SIGNATURE:
            self.format = "protected_nkpi"
            self._parse_header_sizes(header)
            return True
        
        return False
    
    def _parse_header_sizes(self, header):
        """从解密后的文件头中解析各部分大小"""
        self.file_count = struct.unpack('<i', header[24:28])[0]
        self.body_size = struct.unpack('<i', header[32:36])[0]
        self.group_count = struct.unpack('<i', header[36:40])[0]
        self.hash_size = struct.unpack('<i', header[40:44])[0]
        self.name_size = struct.unpack('<i', header[44:48])[0]
    
    def _decrypt_guard(self, buf):
        """对文件头24-28字节进行XOR 0x55预处理"""
        for i in range(24, 28):
            buf[i] ^= 0x55
    
    def _decrypt(self, key, buf, magic):
        """普通解密算法（NKPI格式）"""
        if not key or len(buf) == 0:
            return
        k = key.encode('ascii')
        if len(k) < 4:
            return
        
        size = len(buf)
        seed = (0x76826701 * k[0] + 
                0x1C1 * (k[3] + 0x1C1 * (k[2] + 0x1C1 * k[1]))) & 0xFFFFFFFF
        
        if size >= 4:
            quad_count = size >> 2
            tail = size - (quad_count << 2)
            for idx in range(quad_count):
                t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
                seed = (0x343FD * t1 + magic) & 0xFFFFFFFF
                xor_key = (((seed >> 16) & 0xFFFF) + (t1 & 0xFFFF0000)) & 0xFFFFFFFF
                off = idx << 2
                value = struct.unpack('<I', buf[off:off+4])[0] ^ xor_key
                struct.pack_into('<I', buf, off, value)
        else:
            tail = size
        
        if tail > 0:
            t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
            t2 = (0x343FD * t1 + magic) & 0xFFFFFFFF
            final_key = (t1 & 0xFFFF0000) + ((t2 >> 16) & 0xFFFF)
            key_bytes = struct.pack('<I', final_key)
            start = size - tail
            for idx in range(tail):
                buf[start + idx] ^= key_bytes[idx]
    
    def _decrypt_protected(self, key, buf, magic):
        """受保护格式解密算法（ProtectedNKPI，使用UTF-16密钥）"""
        if not key or len(buf) == 0:
            return
        
        # UTF-16 LE编码密钥
        words = []
        for ch in key:
            words.append(ord(ch))
        if len(words) < 4:
            return
        
        size = len(buf)
        seed = (0x339E9711 * words[0] + 
                0x393 * (words[3] + 0x393 * (words[2] + 0x393 * words[1]))) & 0xFFFFFFFF
        
        if size >= 4:
            quad_count = size >> 2
            tail = size - (quad_count << 2)
            for idx in range(quad_count):
                t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
                seed = (0x343FD * t1 + magic) & 0xFFFFFFFF
                xor_key = ((t1 & 0xFFFF0000) + (seed >> 16)) & 0xFFFFFFFF
                off = idx << 2
                value = struct.unpack('<I', buf[off:off+4])[0] ^ xor_key
                struct.pack_into('<I', buf, off, value)
        else:
            tail = size
        
        if tail > 0:
            t1 = (0x343FD * seed + magic) & 0xFFFFFFFF
            t2 = (0x343FD * t1 + magic) & 0xFFFFFFFF
            final_key = (t1 & 0xFFFF0000) + (t2 >> 16)
            key_bytes = struct.pack('<I', final_key)
            start = size - tail
            for idx in range(tail):
                buf[start + idx] ^= key_bytes[idx]
    
    def _parse_string_pool(self):
        """解析字符串池（strA=UTF-8，strW=UTF-16）"""
        pos = HEADER_SIZE
        table_size = self.file_count * FILE_ITEM_SIZE
        pos += table_size
        pos += self.hash_size
        name_offset = pos
        pos += self.name_size
        group_offset = pos
        group_size = self.group_count * GROUP_ITEM_SIZE
        pos += group_size
        self.body_off = pos
        
        name_bytes = bytearray(self.data[name_offset:name_offset + self.name_size])
        
        if self.format == "protected_nkpi":
            self.str_a = self._decrypt_pstring_buffer(name_bytes, "StRa", 0xAA74472E)
            self.str_w = self._decrypt_pstring_buffer(name_bytes, "StRw", 0x9A82F037)
        else:
            self.str_a = self._decrypt_string_buffer(name_bytes, "sTrA", 0xAA74472E)
            self.str_w = self._decrypt_string_buffer(name_bytes, "sTrW", 0x9A82F037)
        
        print(f"  strA (UTF-8) 大小: {len(self.str_a) if self.str_a else 0} 字节")
        print(f"  strW (UTF-16) 大小: {len(self.str_w) if self.str_w else 0} 字节")
    
    def _decrypt_string_buffer(self, data, key, xor_const):
        """解密普通字符串缓冲区"""
        if len(data) < 16:
            return None
        idx = 8
        
        # strA
        cnt1 = struct.unpack('<I', data[idx:idx+4])[0]
        idx += 4
        idx += 4  # 跳过4字节
        enc_size = cnt1 ^ xor_const
        if enc_size <= 0 or idx + enc_size > len(data):
            return None
        encrypted = bytearray(data[idx:idx+enc_size])
        idx += enc_size
        self._decrypt2(key, encrypted)
        try:
            return zlib.decompress(encrypted)
        except:
            return None
    
    def _decrypt_pstring_buffer(self, data, key, xor_const):
        """解密受保护格式字符串缓冲区"""
        if len(data) < 16:
            return None
        idx = 8
        
        encoded_size = struct.unpack('<I', data[idx:idx+4])[0]
        encoded_original_size = struct.unpack('<I', data[idx+4:idx+8])[0]
        idx += 8
        enc_size = encoded_size ^ xor_const
        if enc_size <= 0 or idx + enc_size > len(data):
            return None
        encrypted = bytearray(data[idx:idx+enc_size])
        idx += enc_size
        self._decrypt_pstring(key, encrypted)
        try:
            return zlib.decompress(encrypted)
        except:
            return None
    
    def _decrypt2(self, key, buf):
        """使用magic 0x269EC9解密（用于字符串池）"""
        self._decrypt(key, buf, 0x269EC9)
    
    def _decrypt_pstring(self, key, buf):
        """使用magic 0x269EC9解密受保护字符串"""
        self._decrypt_protected(key, buf, 0x269EC9)
    
    def _parse_groups(self):
        """解析分组表"""
        pos = HEADER_SIZE
        table_size = self.file_count * FILE_ITEM_SIZE
        pos += table_size
        pos += self.hash_size
        pos += self.name_size
        group_offset = pos
        group_size = self.group_count * GROUP_ITEM_SIZE
        
        group_bytes = bytearray(self.data[group_offset:group_offset + group_size])
        if self.format == "protected_nkpi":
            self._decrypt_protected("grpi", group_bytes, 0x269EC3)
        else:
            self._decrypt("GRPI", group_bytes, 0x269EC3)
        
        self.groups = []
        for idx in range(self.group_count):
            off = idx * GROUP_ITEM_SIZE
            compressed_size = struct.unpack('<i', group_bytes[off:off+4])[0]
            original_size = struct.unpack('<i', group_bytes[off+4:off+8])[0]
            self.groups.append({
                'compressed_size': compressed_size,
                'original_size': original_size
            })
        
        print(f"  解析了 {len(self.groups)} 个数据块")
    
    def _parse_files(self):
        """解析文件表"""
        table_offset = HEADER_SIZE
        
        self.items = []
        self.files = []
        for idx in range(self.file_count):
            off = table_offset + idx * FILE_ITEM_SIZE
            item = {
                'name_offset': struct.unpack('<i', self.data[off:off+4])[0],
                'path_offset': struct.unpack('<i', self.data[off+4:off+8])[0],
                'chunk_index': struct.unpack('<i', self.data[off+8:off+12])[0],
                'data_offset': struct.unpack('<i', self.data[off+12:off+16])[0],
                'data_size': struct.unpack('<i', self.data[off+16:off+20])[0],
                'data_type': struct.unpack('<i', self.data[off+20:off+24])[0],
            }
            self.items.append(item)
            
            name = self._resolve_string(item['name_offset'])
            path = self._resolve_string(item['path_offset'])
            archive_path = f"{path}/{name}" if path else name
            
            file_info = {
                'index': idx,
                'path': path,
                'name': name,
                'archive_path': archive_path,
                'data_type': item['data_type'],
                'size': item['data_size'],
            }
            self.files.append(file_info)
            
            if archive_path:
                key = archive_path.lower().replace('\\', '/')
                if key not in self.path_idx:
                    self.path_idx[key] = idx
        
        print(f"  解析了 {len(self.files)} 个文件")
    
    def _resolve_string(self, magic_offset):
        """解析字符串偏移，最低位表示类型（0=UTF-8，1=UTF-16）"""
        if magic_offset < 0:
            return ""
        if magic_offset & 1:
            return self._read_utf16_string(self.str_w, (magic_offset >> 1) * 2)
        return self._read_utf8_string(self.str_a, magic_offset >> 1)
    
    def _read_utf8_string(self, buf, start):
        """读取UTF-8/GB18030字符串"""
        if not buf or start < 0 or start >= len(buf):
            return ""
        end = buf.find(b'\x00', start)
        if end < 0:
            return ""
        raw = buf[start:end]
        try:
            return raw.decode('utf-8')
        except:
            try:
                return raw.decode('gb18030')
            except:
                return raw.decode('latin-1', errors='replace')
    
    def _read_utf16_string(self, buf, start):
        """读取UTF-16 LE字符串"""
        if not buf or start < 0 or start >= len(buf):
            return ""
        end = start
        while end + 1 < len(buf):
            if buf[end] == 0 and buf[end+1] == 0:
                break
            end += 2
        if end <= start:
            return ""
        try:
            return buf[start:end].decode('utf-16-le')
        except:
            return ""
    
    def get_chunk(self, idx):
        """获取并解密解压数据块"""
        if idx in self.chunks:
            return self.chunks[idx]
        
        if idx < 0 or idx >= len(self.groups):
            return None
        
        prev = 0
        if idx > 0:
            prev = self.groups[idx-1]['compressed_size']
        curr = self.groups[idx]['compressed_size']
        
        start = self.body_off + prev
        size = curr - prev
        
        if start < 0 or size <= 0 or start + size > len(self.data):
            return None
        
        encrypted = bytearray(self.data[start:start+size])
        if self.format == "protected_nkpi":
            self._decrypt_protected("bODy", encrypted, 0x269EC3)
        else:
            self._decrypt("BodY", encrypted, 0x269EC3)
        
        try:
            chunk = zlib.decompress(encrypted)
        except:
            return None
        
        self.chunks[idx] = chunk
        return chunk
    
    def read_file_raw(self, archive_path):
        """读取文件原始数据"""
        key = archive_path.lower().replace('\\', '/')
        if key not in self.path_idx:
            return None
        idx = self.path_idx[key]
        return self.read_file_by_index(idx)
    
    def read_file_by_index(self, idx):
        """按索引读取文件原始数据"""
        if idx < 0 or idx >= len(self.items):
            return None
        item = self.items[idx]
        chunk = self.get_chunk(item['chunk_index'])
        if chunk is None:
            return None
        if item['data_offset'] < 0 or item['data_size'] < 0:
            return None
        if item['data_offset'] + item['data_size'] > len(chunk):
            return None
        return chunk[item['data_offset']:item['data_offset']+item['data_size']]
    
    def read_file_text(self, archive_path):
        """读取文件文本内容"""
        key = archive_path.lower().replace('\\', '/')
        if key not in self.path_idx:
            return None
        idx = self.path_idx[key]
        raw = self.read_file_by_index(idx)
        if raw is None:
            return None
        
        data_type = self.items[idx]['data_type']
        if data_type == 1:
            return self._decode_script(raw)
        elif data_type == 3:
            return raw.decode('utf-16-le', errors='replace')
        return raw.decode('utf-8', errors='replace')
    
    def _decode_script(self, raw):
        """解码脚本类型文件（data_type=1）"""
        line_count = len(raw) // 5
        if line_count == 0:
            return ""
        result = []
        for idx in range(line_count):
            off = idx * 5
            token_type = raw[off]
            value = struct.unpack('<i', raw[off+1:off+5])[0]
            if token_type == 0:
                result.append(f"{value} ")
            elif token_type == 2:
                import struct as _struct
                fval = _struct.unpack('<f', _struct.pack('<i', value))[0]
                result.append(f"{fval:.2f} ")
            elif token_type == 3:
                result.append('\n')
                result.append(self._resolve_string(value))
                result.append('\n')
            elif token_type == 5:
                result.append('\n{5=``}')
            elif token_type == 6:
                result.append(f'`{self._resolve_string(value)}` ')
            elif token_type == 7:
                result.append('\n{7=``}')
        return ''.join(result)
    
    def get_summary(self):
        """获取解析摘要"""
        return {
            'path': self.pvf_path,
            'size': len(self.data),
            'format': self.format,
            'file_count': self.file_count,
            'group_count': self.group_count,
            'body_size': self.body_size,
            'hash_size': self.hash_size,
            'name_size': self.name_size,
            'body_offset': self.body_off,
        }
    
    def list_files(self, limit=None):
        """列出文件"""
        if limit:
            return self.files[:limit]
        return self.files
    
    def find_files_by_extension(self, ext):
        """按扩展名查找文件"""
        ext = ext.lower()
        result = []
        for f in self.files:
            if f['name'].lower().endswith(ext):
                result.append(f)
        return result
    
    def find_files_by_path(self, path_prefix):
        """按路径前缀查找文件"""
        path_prefix = path_prefix.lower().replace('\\', '/')
        result = []
        for f in self.files:
            if f['archive_path'].lower().startswith(path_prefix):
                result.append(f)
        return result


def main():
    """主函数：解析PVF文件并输出结果"""
    import sys
    
    pvf_path = r"C:\Users\56518\Downloads\DNF90-external-oneclick\runtime\data\dnf\Script.pvf"
    
    print("=" * 60)
    print("DNF 90版本 PVF文件解析器（基于服务端源码）")
    print("=" * 60)
    print()
    
    parser = PVFParser(pvf_path)
    parser.load()
    
    print()
    print("=" * 60)
    print("解析摘要")
    print("=" * 60)
    summary = parser.get_summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")
    
    print()
    print("=" * 60)
    print("文件统计")
    print("=" * 60)
    
    # 按扩展名统计
    ext_count = {}
    for f in parser.files:
        ext = os.path.splitext(f['name'])[1].lower()
        ext_count[ext] = ext_count.get(ext, 0) + 1
    
    print("\n按扩展名统计（前20）:")
    sorted_exts = sorted(ext_count.items(), key=lambda x: x[1], reverse=True)
    for i, (ext, count) in enumerate(sorted_exts[:20]):
        print(f"  {i+1:2d}. {ext:10s} : {count:6d}")
    
    # 按目录统计
    dir_count = {}
    for f in parser.files:
        top_dir = f['path'].split('/')[0] if '/' in f['path'] else f['path']
        dir_count[top_dir] = dir_count.get(top_dir, 0) + 1
    
    print("\n按顶层目录统计（前20）:")
    sorted_dirs = sorted(dir_count.items(), key=lambda x: x[1], reverse=True)
    for i, (d, count) in enumerate(sorted_dirs[:20]):
        print(f"  {i+1:2d}. {d:30s} : {count:6d}")
    
    print()
    print("=" * 60)
    print("部分文件列表（前50）")
    print("=" * 60)
    for i, f in enumerate(parser.files[:50]):
        print(f"  {i+1:3d}. [{f['data_type']:2d}] [{f['size']:8d}] {f['archive_path']}")
    
    # 保存结果到JSON
    output_path = r"C:\Users\56518\Downloads\DBObject\pvf_parse_result_v2.json"
    result = {
        'summary': summary,
        'extension_stats': dict(sorted_exts),
        'directory_stats': dict(sorted_dirs),
        'files': [
            {
                'index': f['index'],
                'path': f['path'],
                'name': f['name'],
                'archive_path': f['archive_path'],
                'data_type': f['data_type'],
                'size': f['size'],
            }
            for f in parser.files[:1000]
        ]
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✓ 解析结果已保存到: {output_path}")
    
    # 尝试读取几个特殊文件
    print()
    print("=" * 60)
    print("尝试读取特殊文件")
    print("=" * 60)
    
    special_files = [
        "stringtable.bin",
        "n_string.lst",
    ]
    
    for sf in special_files:
        raw = parser.read_file_raw(sf)
        if raw:
            print(f"\n  {sf}: 找到！大小: {len(raw)} 字节")
            print(f"    前32字节: {raw[:32].hex()}")
        else:
            print(f"\n  {sf}: 未找到")
    
    # 查找stk文件
    stk_files = parser.find_files_by_extension('.stk')
    print(f"\n  .stk文件数量: {len(stk_files)}")
    if stk_files:
        print(f"  前5个:")
        for f in stk_files[:5]:
            print(f"    - {f['archive_path']}")
    
    # 查找lst文件
    lst_files = parser.find_files_by_extension('.lst')
    print(f"\n  .lst文件数量: {len(lst_files)}")
    if lst_files:
        print(f"  前5个:")
        for f in lst_files[:5]:
            print(f"    - {f['archive_path']}")


if __name__ == '__main__':
    main()
