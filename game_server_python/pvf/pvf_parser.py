"""
PVF文件解析模块
负责解析和加载DNF的PVF数据文件
"""

import os
import struct
import threading
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class PVFFileEntry:
    """PVF文件条目"""
    path: str = ""
    offset: int = 0
    size: int = 0
    compressed_size: int = 0
    is_compressed: bool = False
    data: Optional[bytes] = None


@dataclass
class PVFChunk:
    """PVF数据块"""
    index: int = 0
    offset: int = 0
    size: int = 0
    loaded: bool = False
    data: Optional[bytes] = None


class PVFParser:
    """PVF文件解析器"""
    
    # PVF文件头魔数
    PVF_MAGIC = b'PVF\x00'
    PVF_MAGIC2 = b'#PVF_File'
    
    def __init__(self, pvf_path: str = ""):
        self.pvf_path = pvf_path
        self.file_handle = None
        self._loaded = False
        self._lock = threading.Lock()
        
        # 文件信息
        self.file_size: int = 0
        self.version: int = 0
        self.file_count: int = 0
        
        # 文件索引
        self.file_entries: Dict[str, PVFFileEntry] = {}
        self.file_list: List[str] = []
        
        # 数据块缓存
        self.chunk_cache: Dict[int, PVFChunk] = {}
        self.text_cache: Dict[str, str] = {}
        
        # 缓存配置
        self.max_chunk_cache_size: int = 100 * 1024 * 1024  # 100MB
        self.max_text_cache_size: int = 64 * 1024 * 1024  # 64MB
    
    def load(self, pvf_path: str = "") -> bool:
        """加载PVF文件"""
        if pvf_path:
            self.pvf_path = pvf_path
        
        if not self.pvf_path or not os.path.exists(self.pvf_path):
            print(f"[PVFParser] PVF文件不存在: {self.pvf_path}")
            return False
        
        try:
            self.file_size = os.path.getsize(self.pvf_path)
            self.file_handle = open(self.pvf_path, 'rb')
            
            # 读取文件头
            self._read_header()
            
            # 读取文件索引
            self._read_index()
            
            self._loaded = True
            print(f"[PVFParser] PVF文件加载成功: {self.pvf_path}")
            print(f"[PVFParser] 文件大小: {self.file_size / 1024 / 1024:.2f} MB")
            print(f"[PVFParser] 文件数量: {self.file_count}")
            return True
            
        except Exception as e:
            print(f"[PVFParser] PVF文件加载失败: {e}")
            self.close()
            return False
    
    def _read_header(self):
        """读取文件头"""
        if not self.file_handle:
            return
        
        # 读取前16字节
        header = self.file_handle.read(16)
        
        # 检查魔数
        if header[:4] == self.PVF_MAGIC:
            self.version = struct.unpack('<I', header[4:8])[0]
            self.file_count = struct.unpack('<I', header[8:12])[0]
            print(f"[PVFParser] PVF格式1, 版本: {self.version}, 文件数: {self.file_count}")
        
        elif header[:len(self.PVF_MAGIC2)] == self.PVF_MAGIC2:
            # 文本格式PVF
            self.version = 1
            self.file_count = 0
            print(f"[PVFParser] PVF文本格式")
        
        else:
            # 尝试其他格式
            print(f"[PVFParser] 未知PVF格式, 尝试继续解析...")
            self.version = 0
            self.file_count = 0
    
    def _read_index(self):
        """读取文件索引"""
        if not self.file_handle or self.file_count == 0:
            return
        
        try:
            # 这里需要根据实际的PVF格式来解析索引
            # 由于DNF的PVF格式比较复杂，这里先做基础解析
            # 实际项目中需要根据具体格式实现
            
            # 临时实现：扫描文件中的路径标记
            self._scan_file_entries()
            
        except Exception as e:
            print(f"[PVFParser] 读取索引失败: {e}")
    
    def _scan_file_entries(self):
        """扫描文件条目（临时实现）"""
        # 由于PVF格式复杂，这里先记录基本信息
        # 实际项目中需要实现完整的PVF解析
        pass
    
    def read_file(self, file_path: str) -> Optional[bytes]:
        """读取指定文件内容"""
        if not self._loaded or not self.file_handle:
            return None
        
        with self._lock:
            # 标准化路径
            normalized_path = file_path.replace('\\', '/').lower()
            
            # 检查缓存
            if normalized_path in self.text_cache:
                return self.text_cache[normalized_path].encode('utf-8')
            
            # 查找文件条目
            entry = self.file_entries.get(normalized_path)
            if not entry:
                # 尝试模糊查找
                for key, value in self.file_entries.items():
                    if key.endswith(normalized_path) or normalized_path.endswith(key):
                        entry = value
                        break
            
            if not entry:
                return None
            
            # 读取数据
            try:
                self.file_handle.seek(entry.offset)
                data = self.file_handle.read(entry.size)
                
                # 解压（如果需要）
                if entry.is_compressed:
                    # 这里需要实现解压逻辑
                    pass
                
                return data
                
            except Exception as e:
                print(f"[PVFParser] 读取文件失败: {file_path}, 错误: {e}")
                return None
    
    def read_text_file(self, file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """读取文本文件内容"""
        data = self.read_file(file_path)
        if data is None:
            return None
        
        try:
            # 尝试多种编码
            for enc in [encoding, 'gbk', 'gb2312', 'utf-8-sig']:
                try:
                    text = data.decode(enc)
                    # 缓存文本
                    normalized_path = file_path.replace('\\', '/').lower()
                    self.text_cache[normalized_path] = text
                    return text
                except UnicodeDecodeError:
                    continue
            
            # 所有编码都失败，返回原始字节的字符串表示
            return str(data)
            
        except Exception as e:
            print(f"[PVFParser] 读取文本文件失败: {file_path}, 错误: {e}")
            return None
    
    def file_exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        normalized_path = file_path.replace('\\', '/').lower()
        return normalized_path in self.file_entries
    
    def list_files(self, directory: str = "") -> List[str]:
        """列出指定目录下的文件"""
        if not directory:
            return self.file_list.copy()
        
        normalized_dir = directory.replace('\\', '/').lower()
        if not normalized_dir.endswith('/'):
            normalized_dir += '/'
        
        return [f for f in self.file_list if f.startswith(normalized_dir)]
    
    def search_files(self, keyword: str) -> List[str]:
        """搜索文件"""
        keyword_lower = keyword.lower()
        return [f for f in self.file_list if keyword_lower in f.lower()]
    
    def get_item_name(self, item_id: int) -> Optional[str]:
        """根据物品ID获取物品名称（需要从PVF中解析）"""
        # 这里需要实现从PVF中解析物品名称的逻辑
        # 由于PVF格式复杂，这里先返回None
        return None
    
    def close(self):
        """关闭PVF文件"""
        with self._lock:
            if self.file_handle:
                try:
                    self.file_handle.close()
                except Exception:
                    pass
                self.file_handle = None
            
            self._loaded = False
            self.file_entries.clear()
            self.file_list.clear()
            self.chunk_cache.clear()
            self.text_cache.clear()
            
            print("[PVFParser] PVF文件已关闭")
    
    def is_loaded(self) -> bool:
        """PVF文件是否已加载"""
        return self._loaded


class PVFCacheManager:
    """PVF缓存管理器"""
    
    def __init__(self):
        self.parser: Optional[PVFParser] = None
        self._lock = threading.Lock()
    
    def load(self, pvf_path: str) -> bool:
        """加载PVF文件"""
        with self._lock:
            if self.parser and self.parser.is_loaded():
                self.parser.close()
            
            self.parser = PVFParser(pvf_path)
            return self.parser.load()
    
    def get_parser(self) -> Optional[PVFParser]:
        """获取PVF解析器"""
        return self.parser
    
    def close(self):
        """关闭PVF缓存"""
        with self._lock:
            if self.parser:
                self.parser.close()
                self.parser = None


# 全局PVF缓存管理器实例
_pvf_cache_manager: Optional[PVFCacheManager] = None


def get_pvf_cache_manager() -> PVFCacheManager:
    """获取全局PVF缓存管理器实例"""
    global _pvf_cache_manager
    if _pvf_cache_manager is None:
        _pvf_cache_manager = PVFCacheManager()
    return _pvf_cache_manager


def init_pvf(pvf_path: str) -> bool:
    """初始化全局PVF缓存"""
    global _pvf_cache_manager
    _pvf_cache_manager = PVFCacheManager()
    return _pvf_cache_manager.load(pvf_path)
