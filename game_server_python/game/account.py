"""
账号管理模块
负责账号验证、注册、登录等逻辑
"""

import time
import hashlib
import threading
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    print("[AccountManager] 警告: bcrypt 未安装，将使用简单密码哈希")


@dataclass
class AccountInfo:
    """账号信息"""
    id: int = 0
    username: str = ""
    password: str = ""
    email: str = ""
    create_time: int = 0
    last_login_time: int = 0
    status: int = 1  # 1=正常, 0=禁用
    user_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoginSession:
    """登录会话"""
    account_id: int = 0
    username: str = ""
    session_token: str = ""
    login_time: int = 0
    last_active: int = 0
    ip_address: str = ""
    user_data: Dict[str, Any] = field(default_factory=dict)


class AccountManager:
    """账号管理器"""
    
    def __init__(self):
        self.db_manager = None
        self._sessions: Dict[str, LoginSession] = {}
        self._lock = threading.Lock()
        self._initialized = False
    
    def init(self, db_manager) -> bool:
        """初始化账号管理器"""
        self.db_manager = db_manager
        self._initialized = True
        print("[AccountManager] 账号管理器初始化完成")
        return True
    
    def hash_password(self, password: str) -> str:
        """密码哈希"""
        if BCRYPT_AVAILABLE:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # 简单哈希（不推荐，仅用于开发）
            return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码"""
        if BCRYPT_AVAILABLE:
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            except Exception:
                pass
        
        # 简单哈希验证
        simple_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        return simple_hash == stored_hash
    
    def login(self, username: str, password: str, ip_address: str = "") -> Tuple[bool, str, Optional[LoginSession]]:
        """账号登录"""
        if not self._initialized or not self.db_manager:
            return False, "账号管理器未初始化", None
        
        if not username or not password:
            return False, "用户名和密码不能为空", None
        
        # 获取账号信息
        account = self.db_manager.get_account_by_username(username)
        if not account:
            return False, "账号不存在", None
        
        # 检查账号状态
        status = account.get('status', 1)
        if status == 0:
            return False, "账号已被禁用", None
        
        # 验证密码
        stored_password = account.get('password') or account.get('password_hash') or account.get('pwd')
        if not stored_password:
            return False, "账号密码字段不存在", None
        
        if not self.verify_password(password, stored_password):
            # 也尝试明文密码比较（兼容旧数据）
            if stored_password != password:
                return False, "密码错误", None
        
        # 创建登录会话
        account_id = account.get('id', 0)
        session_token = self._generate_session_token(username)
        
        session = LoginSession(
            account_id=account_id,
            username=username,
            session_token=session_token,
            login_time=int(time.time()),
            last_active=int(time.time()),
            ip_address=ip_address,
        )
        
        # 保存会话
        with self._lock:
            self._sessions[session_token] = session
        
        # 更新最后登录时间
        self._update_last_login(account_id)
        
        print(f"[AccountManager] 账号登录成功: {username} (ID: {account_id})")
        return True, "登录成功", session
    
    def register(self, username: str, password: str, email: str = "") -> Tuple[bool, str]:
        """账号注册"""
        if not self._initialized or not self.db_manager:
            return False, "账号管理器未初始化"
        
        if not username or not password:
            return False, "用户名和密码不能为空"
        
        if len(username) < 3:
            return False, "用户名长度不能少于3位"
        
        if len(password) < 6:
            return False, "密码长度不能少于6位"
        
        # 检查账号是否已存在
        existing = self.db_manager.get_account_by_username(username)
        if existing:
            return False, "账号已存在"
        
        # 密码哈希
        password_hash = self.hash_password(password)
        
        # 插入账号（尝试不同的表名和字段名）
        current_time = int(time.time())
        
        insert_queries = [
            (
                f"INSERT INTO {self.db_manager.get_table_name('accounts')} (username, password, email, create_time, status) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, email, current_time, 1)
            ),
            (
                f"INSERT INTO {self.db_manager.get_table_name('account')} (username, password, email, create_time, status) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, email, current_time, 1)
            ),
            (
                f"INSERT INTO accounts (username, password, email, create_time, status) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, email, current_time, 1)
            ),
        ]
        
        # MySQL使用%s占位符
        if self.db_manager.mode == "mysql":
            insert_queries = [
                (sql.replace("?", "%s"), params) for sql, params in insert_queries
            ]
        
        for sql, params in insert_queries:
            try:
                if self.db_manager.execute(sql, params):
                    print(f"[AccountManager] 账号注册成功: {username}")
                    return True, "注册成功"
            except Exception as e:
                print(f"[AccountManager] 注册尝试失败: {e}")
                continue
        
        return False, "注册失败，请稍后重试"
    
    def logout(self, session_token: str) -> bool:
        """账号登出"""
        with self._lock:
            if session_token in self._sessions:
                del self._sessions[session_token]
                print(f"[AccountManager] 账号登出成功: {session_token}")
                return True
        return False
    
    def get_session(self, session_token: str) -> Optional[LoginSession]:
        """获取登录会话"""
        with self._lock:
            session = self._sessions.get(session_token)
            if session:
                session.last_active = int(time.time())
            return session
    
    def verify_session(self, session_token: str) -> bool:
        """验证会话是否有效"""
        session = self.get_session(session_token)
        if not session:
            return False
        
        # 检查会话是否过期（24小时）
        if int(time.time()) - session.login_time > 24 * 3600:
            self.logout(session_token)
            return False
        
        return True
    
    def _generate_session_token(self, username: str) -> str:
        """生成会话令牌"""
        raw = f"{username}_{time.time()}_{threading.get_ident()}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    
    def _update_last_login(self, account_id: int):
        """更新最后登录时间"""
        if not self.db_manager:
            return
        
        current_time = int(time.time())
        update_queries = [
            f"UPDATE {self.db_manager.get_table_name('accounts')} SET last_login_time = ? WHERE id = ?",
            f"UPDATE {self.db_manager.get_table_name('account')} SET last_login_time = ? WHERE id = ?",
            f"UPDATE accounts SET last_login_time = ? WHERE id = ?",
        ]
        
        # MySQL使用%s占位符
        if self.db_manager.mode == "mysql":
            update_queries = [sql.replace("?", "%s") for sql in update_queries]
        
        for sql in update_queries:
            try:
                if self.db_manager.execute(sql, (current_time, account_id)):
                    return
            except Exception:
                continue
    
    def get_online_count(self) -> int:
        """获取在线账号数"""
        with self._lock:
            return len(self._sessions)
    
    def cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = int(time.time())
        expired_tokens = []
        
        with self._lock:
            for token, session in self._sessions.items():
                if current_time - session.login_time > 24 * 3600:
                    expired_tokens.append(token)
            
            for token in expired_tokens:
                del self._sessions[token]
        
        if expired_tokens:
            print(f"[AccountManager] 清理了 {len(expired_tokens)} 个过期会话")


# 全局账号管理器实例
_account_manager: Optional[AccountManager] = None


def get_account_manager() -> AccountManager:
    """获取全局账号管理器实例"""
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
    return _account_manager


def init_account_manager(db_manager) -> bool:
    """初始化全局账号管理器"""
    global _account_manager
    _account_manager = AccountManager()
    return _account_manager.init(db_manager)
