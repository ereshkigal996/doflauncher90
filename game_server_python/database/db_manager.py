"""
数据库管理模块
支持 MySQL 和 SQLite 双模式
"""

import os
import sqlite3
import threading
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

try:
    import pymysql
    from pymysql.cursors import DictCursor
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False
    print("[DatabaseManager] 警告: pymysql 未安装，MySQL模式不可用")


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.mode = "mysql"  # sqlite / mysql
        self.db_path = ""
        self.mysql_config = {}
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        self._mysql_conn = None
        self._lock = threading.Lock()
        self._connected = False
        self.table_prefix = "dnf"
        self.shard_id = "9999"
    
    def init_from_config(self, config) -> bool:
        """从配置初始化数据库"""
        db_config = config.database
        self.mode = db_config.mode
        self.table_prefix = "dnf"
        self.shard_id = config.game.shard_id
        
        if self.mode == "sqlite":
            self.db_path = db_config.path
            # 转换为绝对路径
            if not os.path.isabs(self.db_path):
                # 优先使用配置文件所在目录
                if hasattr(config, 'config_path') and config.config_path:
                    config_dir = os.path.dirname(config.config_path)
                    candidate = os.path.join(config_dir, self.db_path)
                    if os.path.exists(os.path.dirname(candidate)) or os.path.exists(candidate):
                        self.db_path = candidate
                    else:
                        # 回退到当前工作目录
                        self.db_path = os.path.abspath(self.db_path)
                else:
                    # 使用当前工作目录
                    self.db_path = os.path.abspath(self.db_path)
            return self._connect_sqlite()
        
        elif self.mode == "mysql" or self.mode == "portable":
            if not MYSQL_AVAILABLE:
                print("[DatabaseManager] 错误: pymysql 未安装，无法使用MySQL模式")
                return False
            
            self.mysql_config = {
                'host': db_config.host,
                'port': db_config.port,
                'user': db_config.user,
                'password': db_config.password,
                'database': db_config.name,
                'charset': 'utf8mb4',
                'cursorclass': DictCursor,
            }
            return self._connect_mysql()
        
        else:
            print(f"[DatabaseManager] 错误: 未知的数据库模式: {self.mode}")
            return False
    
    def _connect_sqlite(self) -> bool:
        """连接SQLite数据库"""
        try:
            # 确保目录存在
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            self._sqlite_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._sqlite_conn.row_factory = sqlite3.Row
            self._connected = True
            print(f"[DatabaseManager] SQLite连接成功: {self.db_path}")
            return True
            
        except Exception as e:
            print(f"[DatabaseManager] SQLite连接失败: {e}")
            return False
    
    def _connect_mysql(self) -> bool:
        """连接MySQL数据库"""
        try:
            self._mysql_conn = pymysql.connect(**self.mysql_config)
            self._connected = True
            print(f"[DatabaseManager] MySQL连接成功: {self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['database']}")
            return True
            
        except Exception as e:
            print(f"[DatabaseManager] MySQL连接失败: {e}")
            return False
    
    @contextmanager
    def get_cursor(self):
        """获取数据库游标（上下文管理器）"""
        if not self._connected:
            raise Exception("数据库未连接")
        
        with self._lock:
            if self.mode == "sqlite":
                cursor = self._sqlite_conn.cursor()
                try:
                    yield cursor
                    self._sqlite_conn.commit()
                finally:
                    cursor.close()
            
            else:  # mysql
                cursor = self._mysql_conn.cursor()
                try:
                    yield cursor
                    self._mysql_conn.commit()
                finally:
                    cursor.close()
    
    def execute(self, sql: str, params: Tuple = ()) -> bool:
        """执行SQL语句"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
            return True
        except Exception as e:
            print(f"[DatabaseManager] 执行失败: {e}")
            print(f"[DatabaseManager] SQL: {sql}")
            return False
    
    def query(self, sql: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """查询数据"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                
                # 转换为dict列表
                result = []
                for row in rows:
                    if isinstance(row, sqlite3.Row):
                        result.append(dict(row))
                    else:
                        result.append(row)
                return result
                
        except Exception as e:
            print(f"[DatabaseManager] 查询失败: {e}")
            print(f"[DatabaseManager] SQL: {sql}")
            return []
    
    def query_one(self, sql: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """查询单条数据"""
        results = self.query(sql, params)
        return results[0] if results else None
    
    def get_table_name(self, base_name: str) -> str:
        """获取带前缀的表名"""
        return f"{self.table_prefix}_{base_name}"
    
    # ========== 账号相关操作 ==========
    
    def get_account_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取账号信息"""
        # 尝试不同的表名和字段名
        possible_queries = [
            (f"SELECT * FROM {self.get_table_name('accounts')} WHERE username = %s", (username,)),
            (f"SELECT * FROM {self.get_table_name('account')} WHERE username = %s", (username,)),
            (f"SELECT * FROM accounts WHERE username = %s", (username,)),
            (f"SELECT * FROM account WHERE username = %s", (username,)),
        ]
        
        # SQLite使用?占位符
        if self.mode == "sqlite":
            possible_queries = [
                (sql.replace("%s", "?"), params) for sql, params in possible_queries
            ]
        
        for sql, params in possible_queries:
            try:
                result = self.query_one(sql, params)
                if result:
                    return result
            except Exception:
                continue
        
        return None
    
    def verify_account(self, username: str, password: str) -> Tuple[bool, str]:
        """验证账号密码"""
        account = self.get_account_by_username(username)
        if not account:
            return False, "账号不存在"
        
        # 尝试不同的密码字段名
        stored_password = account.get('password') or account.get('password_hash') or account.get('pwd')
        
        if not stored_password:
            return False, "账号密码字段不存在"
        
        # 简单密码验证（实际应该使用bcrypt等加密）
        if stored_password == password:
            return True, "登录成功"
        
        # 尝试bcrypt验证
        try:
            import bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                return True, "登录成功"
        except Exception:
            pass
        
        return False, "密码错误"
    
    # ========== 角色相关操作 ==========
    
    def get_characters_by_account_id(self, account_id: int) -> List[Dict[str, Any]]:
        """根据账号ID获取角色列表"""
        possible_queries = [
            f"SELECT * FROM {self.get_table_name('characters')} WHERE account_id = {account_id}",
            f"SELECT * FROM {self.get_table_name('character')} WHERE account_id = {account_id}",
            f"SELECT * FROM characters WHERE account_id = {account_id}",
            f"SELECT * FROM character WHERE account_id = {account_id}",
        ]
        
        for sql in possible_queries:
            try:
                results = self.query(sql)
                if results:
                    return results
            except Exception:
                continue
        
        return []
    
    def get_character_by_id(self, character_id: int) -> Optional[Dict[str, Any]]:
        """根据角色ID获取角色信息"""
        possible_queries = [
            f"SELECT * FROM {self.get_table_name('characters')} WHERE id = {character_id}",
            f"SELECT * FROM {self.get_table_name('character')} WHERE id = {character_id}",
            f"SELECT * FROM characters WHERE id = {character_id}",
            f"SELECT * FROM character WHERE id = {character_id}",
        ]
        
        for sql in possible_queries:
            try:
                result = self.query_one(sql)
                if result:
                    return result
            except Exception:
                continue
        
        return None
    
    # ========== 数据库状态 ==========
    
    def is_connected(self) -> bool:
        """数据库是否已连接"""
        return self._connected
    
    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._sqlite_conn:
                self._sqlite_conn.close()
                self._sqlite_conn = None
            
            if self._mysql_conn:
                self._mysql_conn.close()
                self._mysql_conn = None
            
            self._connected = False
            print("[DatabaseManager] 数据库连接已关闭")
    
    def ping(self) -> bool:
        """检查数据库连接是否有效"""
        try:
            if self.mode == "sqlite":
                self.query("SELECT 1")
            else:
                self._mysql_conn.ping()
            return True
        except Exception:
            return False


# 全局数据库管理器实例
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database(config) -> bool:
    """初始化全局数据库"""
    global _db_manager
    _db_manager = DatabaseManager()
    return _db_manager.init_from_config(config)
