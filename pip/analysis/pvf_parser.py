# -*- coding: utf-8 -*-
"""
PVF文件解析器模块
基于 https://github.com/similing4/pvf 的C#实现移植到Python

功能：
1. 读取PVF文件列表
2. 按路径提取文件内容（转成可读文本）
3. 解析stringtable.bin和n_string.lst
4. 支持脚本文件(.skl等)的文本化解析
"""

import struct
import os
from typing import Dict, List, Optional, Tuple


class PvfHeader:
    """PVF文件头"""
    def __init__(self):
        self.uuid_length = 0
        self.uuid = b""
        self.file_version = 0
        self.dir_tree_length = 0
        self.dir_tree_crc32 = 0
        self.num_files = 0


class PvfFileNode:
    """PVF文件树节点"""
    def __init__(self):
        self.file_number = 0
        self.file_path = ""
        self.file_length = 0
        self.file_crc32 = 0
        self.relative_offset = 0
        self.unpacked_data = None  # 解密后的文件内容


class PvfParser:
    """PVF文件解析器"""
    
    # 解密密钥
    DECRYPT_KEY = 0x81A79011
    
    def __init__(self, pvf_path: str):
        self.pvf_path = pvf_path
        self.header = PvfHeader()
        self.file_tree: Dict[str, PvfFileNode] = {}  # 路径小写 -> 节点
        self.string_table: Dict[int, str] = {}  # 索引 -> 字符串
        self.n_string_map: Dict[str, str] = {}  # 键 -> 值
        self._file = None
    
    def open(self):
        """打开并解析PVF文件"""
        self._file = open(self.pvf_path, 'rb')
        self._parse_header()
        self._decrypt_and_parse_file_tree()
        self._load_string_table()
        self._load_n_string_lst()
    
    def close(self):
        """关闭文件"""
        if self._file:
            self._file.close()
            self._file = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def _read_uint32(self) -> int:
        """读取4字节无符号整数（小端）"""
        data = self._file.read(4)
        return struct.unpack('<I', data)[0]
    
    def _read_int32(self) -> int:
        """读取4字节有符号整数（小端）"""
        data = self._file.read(4)
        return struct.unpack('<i', data)[0]
    
    @staticmethod
    def _decrypt_data(data: bytes, crc32: int) -> bytes:
        """
        解密数据
        算法：逐4字节，与key^crc32异或，后6位移到最前面
        """
        key = PvfParser.DECRYPT_KEY
        result = bytearray(len(data))
        
        for i in range(0, len(data) - 3, 4):
            # 读取4字节小端整数
            num = struct.unpack('<I', data[i:i+4])[0]
            # 异或
            num = num ^ key ^ crc32
            # 后6位移到前面，前26位移到后面
            num = ((num >> 6) | (num << 26)) & 0xFFFFFFFF
            # 写回
            result[i:i+4] = struct.pack('<I', num)
        
        # 处理剩余不足4字节的部分
        remaining = len(data) % 4
        if remaining > 0:
            result[-remaining:] = data[-remaining:]
        
        return bytes(result)
    
    @staticmethod
    def _encrypt_data(data: bytes, crc32: int) -> bytes:
        """
        加密数据（解密的逆操作）
        """
        key = PvfParser.DECRYPT_KEY
        result = bytearray(len(data))
        
        for i in range(0, len(data) - 3, 4):
            num = struct.unpack('<I', data[i:i+4])[0]
            # 前6位移到后面，后26位移到前面
            num = ((num >> 26) | (num << 6)) & 0xFFFFFFFF
            # 异或
            num = num ^ key ^ crc32
            result[i:i+4] = struct.pack('<I', num)
        
        remaining = len(data) % 4
        if remaining > 0:
            result[-remaining:] = data[-remaining:]
        
        return bytes(result)
    
    def _parse_header(self):
        """解析PVF文件头"""
        # UUID长度
        self.header.uuid_length = self._read_int32()
        # UUID
        self.header.uuid = self._file.read(self.header.uuid_length)
        # 文件版本
        self.header.file_version = self._read_int32()
        # 文件树大小
        self.header.dir_tree_length = self._read_int32()
        # 文件树CRC32（无符号）
        self.header.dir_tree_crc32 = self._read_uint32()
        # 文件数量
        self.header.num_files = self._read_int32()
    
    def _decrypt_and_parse_file_tree(self):
        """解密并解析文件树"""
        # 读取加密的文件树
        encrypted_tree = self._file.read(self.header.dir_tree_length)
        # 解密
        decrypted_tree = self._decrypt_data(encrypted_tree, self.header.dir_tree_crc32)
        
        tree_size = len(decrypted_tree)
        
        # 解析文件树（不依赖num_files，解析到末尾为止）
        pos = 0
        parsed_count = 0
        error_count = 0
        
        while pos + 8 <= tree_size:
            try:
                node = PvfFileNode()
                
                # 文件编号
                node.file_number = struct.unpack_from('<i', decrypted_tree, pos)[0]
                pos += 4
                
                # 文件路径长度
                path_length = struct.unpack_from('<i', decrypted_tree, pos)[0]
                pos += 4
                
                # 边界检查
                if path_length < 0 or path_length > 10000 or pos + path_length + 12 > tree_size:
                    # 异常节点，停止解析
                    break
                
                # 文件路径（CP949/韩语编码，实际可能是BIG5）
                path_bytes = decrypted_tree[pos:pos+path_length]
                pos += path_length
                
                # 尝试多种编码
                for encoding in ['cp949', 'big5', 'utf-8', 'gbk']:
                    try:
                        node.file_path = path_bytes.decode(encoding).replace('\\', '/').lower()
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    node.file_path = path_bytes.decode('utf-8', errors='replace').replace('\\', '/').lower()
                
                # 文件大小
                node.file_length = struct.unpack_from('<i', decrypted_tree, pos)[0]
                pos += 4
                
                # 文件CRC32
                node.file_crc32 = struct.unpack_from('<I', decrypted_tree, pos)[0]
                pos += 4
                
                # 相对偏移
                node.relative_offset = struct.unpack_from('<i', decrypted_tree, pos)[0]
                pos += 4
                
                # 验证节点合理性
                if node.file_length < 0 or node.file_length > 100 * 1024 * 1024:
                    error_count += 1
                    if error_count > 10:
                        break
                    continue
                
                if node.file_path and node.file_path not in self.file_tree:
                    self.file_tree[node.file_path] = node
                    parsed_count += 1
                
            except (struct.error, IndexError, ValueError):
                error_count += 1
                if error_count > 10:
                    break
                continue
        
        # 更新实际文件数量
        self.header.num_files = parsed_count
    
    def _get_file_data(self, node: PvfFileNode) -> bytes:
        """获取并解密单个文件内容"""
        if node.unpacked_data is not None:
            return node.unpacked_data
        
        # 计算实际读取长度（向上取整到4的倍数）
        read_length = (node.file_length + 3) & 0xFFFFFFFC
        
        # 定位到文件内容位置
        # 文件内容起始位置 = 头大小 + 文件树大小
        header_size = 4 + self.header.uuid_length + 4 + 4 + 4 + 4
        file_data_start = header_size + self.header.dir_tree_length
        
        self._file.seek(file_data_start + node.relative_offset)
        encrypted_data = self._file.read(read_length)
        
        # 解密
        decrypted_data = self._decrypt_data(encrypted_data, node.file_crc32)
        
        # 截取实际长度
        node.unpacked_data = decrypted_data[:node.file_length]
        
        return node.unpacked_data
    
    def _load_string_table(self):
        """加载stringtable.bin"""
        if 'stringtable.bin' not in self.file_tree:
            return
        
        node = self.file_tree['stringtable.bin']
        data = self._get_file_data(node)
        
        if len(data) < 4:
            return
        
        # 字符串表长度
        count = struct.unpack_from('<i', data, 0)[0]
        
        # 读取每个字符串的起始和结束位置
        for i in range(count):
            offset = 4 + i * 8
            if offset + 8 > len(data):
                break
            
            start_pos = struct.unpack_from('<i', data, offset)[0]
            end_pos = struct.unpack_from('<i', data, offset + 4)[0]
            str_length = end_pos - start_pos
            
            if str_length > 0 and start_pos + 4 + str_length <= len(data):
                str_bytes = data[start_pos + 4 : start_pos + 4 + str_length]
                # BIG5编码
                for encoding in ['big5', 'cp949', 'utf-8', 'gbk']:
                    try:
                        s = str_bytes.decode(encoding).rstrip('\x00')
                        self.string_table[i] = s
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                else:
                    self.string_table[i] = str_bytes.decode('utf-8', errors='replace')
    
    def _load_n_string_lst(self):
        """加载n_string.lst"""
        if 'n_string.lst' not in self.file_tree:
            return
        
        node = self.file_tree['n_string.lst']
        data = self._get_file_data(node)
        
        if len(data) < 2:
            return
        
        # 前2字节固定为0xB0 0xD0
        if data[0] != 0xB0 or data[1] != 0xD0:
            return
        
        # 从第2字节开始，每10字节一组
        for i in range(2, len(data) - 9, 10):
            # 前6字节未知，6-10字节是stringtable的索引
            string_index = struct.unpack_from('<i', data, i + 6)[0]
            
            if string_index in self.string_table:
                file_path = self.string_table[string_index].lower().strip()
                
                if file_path in self.file_tree:
                    file_node = self.file_tree[file_path]
                    file_content = self._get_file_data(file_node)
                    
                    # 尝试解码
                    for encoding in ['big5', 'cp949', 'utf-8', 'gbk']:
                        try:
                            content_text = file_content.decode(encoding).rstrip('\x00')
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue
                    else:
                        content_text = file_content.decode('utf-8', errors='replace')
                    
                    # 逐行解析 key>value
                    for line in content_text.split('\r\n'):
                        line = line.strip()
                        if '>' in line and not line.startswith('//'):
                            key, _, value = line.partition('>')
                            key = key.strip()
                            value = value.strip()
                            if key and value:
                                self.n_string_map[key] = value
    
    def get_file_list(self) -> List[str]:
        """获取所有文件路径列表"""
        return sorted(self.file_tree.keys())
    
    def get_file_raw(self, path: str) -> Optional[bytes]:
        """获取文件原始二进制内容"""
        path = path.lower().strip()
        if path not in self.file_tree:
            return None
        return self._get_file_data(self.file_tree[path])
    
    def get_file_text(self, path: str, encoding: str = 'utf-8') -> Optional[str]:
        """获取文件文本内容（直接解码，不做脚本解析）"""
        data = self.get_file_raw(path)
        if data is None:
            return None
        
        for enc in [encoding, 'big5', 'cp949', 'gbk', 'utf-8']:
            try:
                return data.decode(enc).rstrip('\x00')
            except (UnicodeDecodeError, LookupError):
                continue
        return data.decode('utf-8', errors='replace')
    
    def parse_script_file(self, path: str) -> Optional[str]:
        """
        解析脚本文件（.skl等），转成可读文本
        格式：前2字节0xB0 0xD0，之后每5字节：1字节标志位 + 4字节数据
        """
        data = self.get_file_raw(path)
        if data is None or len(data) < 2:
            return None
        
        # 检查前2字节
        if data[0] != 0xB0 or data[1] != 0xD0:
            # 不是脚本格式，直接返回文本
            return self.get_file_text(path)
        
        result = ["#PVF_File\r\n"]
        str_pos = 0
        
        # 从第2字节开始，每5字节一组
        i = 2
        while i + 5 <= len(data):
            current_byte = data[i]
            after1 = struct.unpack_from('<i', data, i + 1)[0]
            
            if current_byte == 2:
                # Int
                result.append(f"{after1}\t")
            elif current_byte == 3:
                # IntEx
                result.append(f"{{{current_byte}=`{after1}`}}\t")
            elif current_byte == 4:
                # Float
                float_val = struct.unpack_from('<f', data, i + 1)[0]
                result.append(f"{float_val:.6f}\t")
            elif current_byte == 5:
                # Section
                s = self.string_table.get(after1, "")
                result.append(f"\r\n{s}\r\n")
            elif current_byte == 6 or current_byte == 8:
                # Command / CommandSeparator
                s = self.string_table.get(after1, "")
                result.append(f"{{{current_byte}=`{s}`}}\r\n")
            elif current_byte == 7:
                # String
                s = self.string_table.get(after1, "")
                result.append(f"`{s}`\r\n")
            elif current_byte == 9:
                # StringLinkIndex
                before1 = struct.unpack_from('<i', data, i - 4)[0] if i >= 4 else 0
                s = self.string_table.get(after1, "")
                n_string_val = self.n_string_map.get(s, "")
                result.append(f"<{before1}::{s}`{n_string_val}`>\r\n")
            elif current_byte == 10:
                # StringLink（已在9中处理）
                pass
            
            i += 5
        
        result.append("\r\n")
        return "".join(result)
    
    def search_files(self, keyword: str) -> List[str]:
        """搜索包含关键词的文件路径"""
        keyword = keyword.lower()
        return [path for path in self.file_tree if keyword in path]
    
    def get_file_info(self, path: str) -> Optional[dict]:
        """获取文件信息"""
        path = path.lower().strip()
        if path not in self.file_tree:
            return None
        node = self.file_tree[path]
        return {
            'path': node.file_path,
            'file_number': node.file_number,
            'number': node.file_number,
            'file_length': node.file_length,
            'size': node.file_length,
            'file_crc32': node.file_crc32,
            'crc32': node.file_crc32,
            'relative_offset': node.relative_offset,
            'offset': node.relative_offset,
        }


# 测试代码
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python pvf_parser.py <pvf文件路径> [文件路径]")
        print("示例: python pvf_parser.py Script.pvf skill/gunner/wipeout.skl")
        sys.exit(1)
    
    pvf_path = sys.argv[1]
    target_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    print(f"正在解析: {pvf_path}")
    
    with PvfParser(pvf_path) as parser:
        print(f"文件数量: {parser.header.num_files}")
        print(f"StringTable数量: {len(parser.string_table)}")
        print(f"N_String数量: {len(parser.n_string_map)}")
        
        if target_file:
            print(f"\n正在提取: {target_file}")
            content = parser.parse_script_file(target_file)
            if content:
                print(content[:2000])
                if len(content) > 2000:
                    print(f"\n... (共 {len(content)} 字符)")
            else:
                print("文件不存在")
        else:
            print("\n文件列表（前50个）:")
            files = parser.get_file_list()
            for f in files[:50]:
                info = parser.get_file_info(f)
                print(f"  {f} ({info['size']} bytes)")
            print(f"\n共 {len(files)} 个文件")
