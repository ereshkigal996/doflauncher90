# -*- coding: utf-8 -*-
"""
账号管理模块
对应Go版 account_auth.go
"""

import os
import json
import uuid
import hashlib
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple, List
from datetime import datetime

from core.paths import ProjectPaths
from modules.mysql_manager import MySQLManager


@dataclass
class AccountInfo:
    """账号信息"""
    account_id: str = ""
    username: str = ""
    state: str = ""  # active / disabled
    created_at: str = ""
    updated_at: str = ""
    last_login_at: str = ""


class AccountManager:
    """账号管理器"""
    
    def __init__(self, paths: ProjectPaths, mysql_mgr: MySQLManager):
        self.paths = paths
        self.mysql_mgr = mysql_mgr
    
    def _get_mysql_client(self) -> Optional[str]:
        """获取mysql客户端路径"""
        mysql_exe = os.path.join(self.paths.mysql_server, "bin", "mysql.exe")
        return mysql_exe if os.path.isfile(mysql_exe) else None
    
    def _execute_mysql(self, query: str, database: str = None) -> Tuple[Optional[str], Optional[str]]:
        """执行MySQL命令"""
        mysql_exe = self._get_mysql_client()
        if not mysql_exe:
            return None, "mysql client not found"
        
        config = self.mysql_mgr.config
        args = [
            f"--host={config.host}",
            f"--port={config.port}",
            f"--user={config.user}",
            "--batch",
            "--raw",
        ]
        if config.password:
            args.append(f"--password={config.password}")
        if database:
            args.append(database)
        args.extend(["-e", query])
        
        try:
            result = subprocess.run(
                [mysql_exe] + args,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return None, result.stderr
            return result.stdout, None
        except Exception as e:
            return None, f"mysql execute failed: {e}"
    
    def _hash_password(self, password: str) -> str:
        """
        密码哈希（使用MySQL的PASSWORD函数或bcrypt）
        注意：DNF90使用bcrypt加密
        """
        try:
            import bcrypt
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        except ImportError:
            # 回退到SHA256（仅用于测试）
            return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码"""
        try:
            import bcrypt
            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
        except ImportError:
            # 回退到SHA256验证
            return hashlib.sha256(password.encode('utf-8')).hexdigest() == stored_hash
    
    def register(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """
        注册账号
        对应Go版 account register
        """
        # 验证输入
        if not username or len(username) < 3:
            return False, "username too short (min 3 chars)"
        if not password or len(password) < 6:
            return False, "password too short (min 6 chars)"
        
        # 检查MySQL是否运行
        if not self.mysql_mgr.is_running():
            return False, "MySQL is not running"
        
        # 检查账号是否已存在
        check_query = f"SELECT account_id FROM dnf_login_accounts WHERE username = '{username}'"
        result, err = self._execute_mysql(check_query, "dnf_local")
        if err:
            return False, f"check account failed: {err}"
        if result and result.strip():
            return False, "username already exists"
        
        # 创建账号
        account_id = f"dnf:{uuid.uuid4().hex}"
        password_hash = self._hash_password(password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        insert_query = f"""
            INSERT INTO dnf_login_accounts 
            (account_id, username, password_hash, state, created_at, updated_at, last_login_at)
            VALUES ('{account_id}', '{username}', '{password_hash}', 'active', '{now}', '{now}', '{now}')
        """
        _, err = self._execute_mysql(insert_query, "dnf_local")
        if err:
            return False, f"register failed: {err}"
        
        return True, f"account '{username}' registered successfully"
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[str], Optional[AccountInfo]]:
        """
        登录验证
        对应Go版 account login
        返回: (success, message, account_info)
        """
        if not username or not password:
            return False, "username and password required", None
        
        # 检查MySQL是否运行
        if not self.mysql_mgr.is_running():
            return False, "MySQL is not running", None
        
        # 查询账号
        query = f"SELECT account_id, username, password_hash, state, created_at, updated_at, last_login_at FROM dnf_login_accounts WHERE username = '{username}'"
        result, err = self._execute_mysql(query, "dnf_local")
        if err:
            return False, f"query failed: {err}", None
        
        if not result or not result.strip():
            return False, "account not found", None
        
        # 解析结果
        lines = result.strip().split('\n')
        if len(lines) < 2:
            return False, "invalid query result", None
        
        # 第一行是表头，第二行是数据
        data = lines[1].split('\t')
        if len(data) < 7:
            return False, "invalid account data", None
        
        account_id, db_username, password_hash, state, created_at, updated_at, last_login_at = data[:7]
        
        # 检查账号状态
        if state != 'active':
            return False, f"account is {state}", None
        
        # 验证密码
        if not self._verify_password(password, password_hash):
            return False, "invalid password", None
        
        # 更新最后登录时间
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_query = f"UPDATE dnf_login_accounts SET last_login_at = '{now}' WHERE account_id = '{account_id}'"
        self._execute_mysql(update_query, "dnf_local")
        
        account = AccountInfo(
            account_id=account_id,
            username=db_username,
            state=state,
            created_at=created_at,
            updated_at=updated_at,
            last_login_at=now
        )
        
        return True, "login successful", account
    
    def list_accounts(self) -> Tuple[Optional[List[AccountInfo]], Optional[str]]:
        """
        列出所有账号
        对应Go版 account list
        """
        if not self.mysql_mgr.is_running():
            return None, "MySQL is not running"
        
        query = "SELECT account_id, username, state, created_at, updated_at, last_login_at FROM dnf_login_accounts ORDER BY created_at"
        result, err = self._execute_mysql(query, "dnf_local")
        if err:
            return None, f"query failed: {err}"
        
        if not result or not result.strip():
            return [], None
        
        accounts = []
        lines = result.strip().split('\n')
        for line in lines[1:]:  # 跳过表头
            data = line.split('\t')
            if len(data) >= 6:
                accounts.append(AccountInfo(
                    account_id=data[0],
                    username=data[1],
                    state=data[2],
                    created_at=data[3],
                    updated_at=data[4],
                    last_login_at=data[5]
                ))
        
        return accounts, None
