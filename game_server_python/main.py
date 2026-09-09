#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameServer 服务端 Python 实现
主入口文件

基于 DNF90-external-oneclick 服务端架构
使用 Python 重新实现的单机版服务端

版本: 0.1.0 (开发中)
作者: ereshkigal996
"""

import os
import sys
import time
import signal
import argparse
import threading
from datetime import datetime

# 设置Windows控制台编码为UTF-8，解决中文乱码问题
if sys.platform == 'win32':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    
    # 重新配置标准输出编码
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 添加项目根目录到路径
# 打包后使用可执行文件所在目录，否则使用脚本所在目录
if getattr(sys, 'frozen', False):
    PROJECT_ROOT = os.path.dirname(sys.executable)
else:
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 导入模块
from config.instance import ConfigManager, get_config_manager, init_config
from database.db_manager import DatabaseManager, get_db_manager, init_database
from database.mysql_manager import MySQLManager, init_mysql_manager, get_mysql_manager
from network.base_server import NetworkManager, get_network_manager, init_network
from network.admin_server import AdminHTTPServer, init_admin_server, get_admin_server
from network.channel_server import ChannelServer
from network.game_server import GameServer as NetworkGameServer, GameChannel
from pvf.pvf_parser import PVFCacheManager, get_pvf_cache_manager, init_pvf
from game.account import AccountManager, get_account_manager, init_account_manager
from game.character import CharacterManager, MemoryCharacterRepository
from utils.logger import Logger, get_logger, init_logger
from utils.process import ProcessManager, get_process_manager, init_process_manager


class GameServer:
    """GameServer服务端主类"""
    
    def __init__(self):
        self.version = "0.1.0"
        self.running = False
        self.start_time = 0
        
        # 模块实例
        self.config_manager: ConfigManager = None
        self.db_manager: DatabaseManager = None
        self.mysql_manager: MySQLManager = None
        self.network_manager: NetworkManager = None
        self.admin_server: AdminHTTPServer = None
        self.pvf_manager: PVFCacheManager = None
        self.account_manager: AccountManager = None
        self.character_manager: CharacterManager = None
        self.channel_server: ChannelServer = None
        self.game_server: GameServer = None
        self.logger: Logger = None
        self.process_manager: ProcessManager = None
        
        # 信号处理
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except Exception:
            pass
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print(f"\n[Server] 收到信号: {signum}，正在停止服务端...")
        self.stop()
    
    def init(self, config_path: str = "") -> bool:
        """初始化服务端"""
        print("=" * 60)
        print(f"GameServer 服务端 Python 实现 v{self.version}")
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 1. 初始化日志
        print("\n[1/10] 初始化日志系统...")
        log_dir = os.path.join(PROJECT_ROOT, "data", "logs")
        self.logger = init_logger("GameServer", log_dir)
        self.logger.info(f"GameServer 服务端 Python 实现 v{self.version} 启动中...")
        
        # 2. 加载配置
        print("\n[2/10] 加载配置文件...")
        if not config_path:
            # 尝试默认配置路径
            default_paths = [
                os.path.join(PROJECT_ROOT, "data", "config", "instance.json"),
                os.path.join(PROJECT_ROOT, "instance.json"),
            ]
            for path in default_paths:
                if os.path.exists(path):
                    config_path = path
                    break
        
        if not config_path:
            print("[警告] 未找到配置文件，使用默认配置")
            self.config_manager = get_config_manager()
        else:
            if not init_config(config_path):
                print("[错误] 配置文件加载失败")
                return False
            self.config_manager = get_config_manager()
        
        # 3. 如果是便携版MySQL，先启动MySQL（在连接数据库之前）
        db_mode = self.config_manager.config.database.mode
        if db_mode in ("portable", "mysql"):
            print("\n[3/10] 启动便携版MySQL...")
            server_root = os.path.dirname(os.path.abspath(__file__))
            # 如果是打包后的程序，使用可执行文件所在目录
            if getattr(sys, 'frozen', False):
                server_root = os.path.dirname(sys.executable)
            
            mysql_config = {
                'host': self.config_manager.config.database.host,
                'port': self.config_manager.config.database.port,
                'user': self.config_manager.config.database.user,
                'password': self.config_manager.config.database.password,
            }
            self.mysql_manager = init_mysql_manager(server_root, mysql_config)
            
            # 检查MySQL是否已安装
            if self.mysql_manager.is_installed():
                success, msg = self.mysql_manager.start(wait_timeout=30)
                if success:
                    print(f"[3/10] MySQL启动成功: {msg}")
                    # 等待MySQL完全就绪
                    time.sleep(2)
                else:
                    print(f"[警告] MySQL启动失败: {msg}")
                    print("[警告] 服务端可能无法正常工作，请检查MySQL配置")
            else:
                print("[警告] 便携版MySQL未安装，跳过自动启动")
                print("[警告] 请确保MySQL已手动启动")
        
        # 3.1 初始化数据库连接
        print("\n[3.1/10] 初始化数据库连接...")
        if not init_database(self.config_manager.config):
            print("[错误] 数据库初始化失败")
            return False
        self.db_manager = get_db_manager()
        
        # 4. 初始化PVF缓存
        print("\n[4/10] 初始化PVF文件缓存...")
        pvf_path = self.config_manager.config.game.pvf_path
        if not os.path.isabs(pvf_path):
            # 相对于runtime目录
            config_dir = os.path.dirname(os.path.dirname(self.config_manager.config_path))
            pvf_path = os.path.join(config_dir, pvf_path)
        
        if os.path.exists(pvf_path):
            if not init_pvf(pvf_path):
                print("[警告] PVF文件加载失败，继续启动...")
            self.pvf_manager = get_pvf_cache_manager()
        else:
            print(f"[警告] PVF文件不存在: {pvf_path}")
        
        # 5. 初始化账号管理器
        print("\n[5/10] 初始化账号管理器...")
        if not init_account_manager(self.db_manager):
            print("[错误] 账号管理器初始化失败")
            return False
        self.account_manager = get_account_manager()
        
        # 5.5 初始化角色管理器
        print("\n[5.5/10] 初始化角色管理器...")
        character_repo = MemoryCharacterRepository()
        self.character_manager = CharacterManager(character_repo)
        print("[5.5/10] 角色管理器初始化完成（内存模式）")
        
        # 6. 初始化进程管理器
        print("\n[6/10] 初始化进程管理器...")
        state_dir = os.path.join(PROJECT_ROOT, "data", "state")
        self.process_manager = init_process_manager(state_dir, log_dir)
        
        # 7. 初始化网络服务
        print("\n[7/10] 初始化网络服务...")
        if not init_network(self.config_manager.config):
            print("[错误] 网络服务初始化失败")
            return False
        self.network_manager = get_network_manager()
        
        # 7.5 初始化频道服务器
        print("\n[7.5/10] 初始化频道服务器...")
        channel_host = "0.0.0.0"
        channel_port = 7001
        channel_aes_key = "0123456789abcdef"
        self.channel_server = ChannelServer(
            host=channel_host,
            port=channel_port,
            aes_key=channel_aes_key,
            server_ip="127.0.0.1",
        )
        print(f"[7.5/10] 频道服务器初始化完成（端口 {channel_port}）")
        
        # 7.6 初始化游戏服务器
        print("\n[7.6/10] 初始化游戏服务器...")
        self.game_server = NetworkGameServer(
            host="0.0.0.0",
            aes_key=channel_aes_key,
            server_ip="127.0.0.1",
        )
        # 添加默认游戏频道
        self.game_server.add_channel(GameChannel(
            id=1,
            name="普通频道1",
            port=7002,
            max_users=100,
            current_users=0,
            type="normal",
        ))
        print(f"[7.6/10] 游戏服务器初始化完成（{len(self.game_server.channels)}个频道）")
        
        # 8. 初始化HTTP管理服务器
        print("\n[8/10] 初始化HTTP管理服务...")
        admin_listen = self.config_manager.config.server.admin_listen
        if ":" in admin_listen:
            admin_host, admin_port_str = admin_listen.rsplit(":", 1)
            admin_port = int(admin_port_str)
        else:
            admin_host = "127.0.0.1"
            admin_port = 18111
        
        admin_token = self.config_manager.config.server.admin_token
        self.admin_server = init_admin_server(admin_host, admin_port, admin_token, self.version)
        
        print("\n" + "=" * 60)
        print("服务端初始化完成！")
        print(f"数据库模式: {self.config_manager.config.database.mode}")
        print(f"频道监听: {self.config_manager.config.server.channel_listen}")
        print(f"管理监听: {self.config_manager.config.server.admin_listen}")
        print("=" * 60)
        
        self.logger.info("服务端初始化完成")
        return True
    
    def start(self) -> bool:
        """启动服务端"""
        if self.running:
            print("[警告] 服务端已在运行中")
            return False
        
        print("\n[Server] 正在启动服务端...")
        
        # 启动网络服务
        if not self.network_manager.start():
            print("[错误] 网络服务启动失败")
            return False
        
        # 启动频道服务器
        if self.channel_server:
            try:
                self.channel_server.start()
                print(f"[Server] 频道服务器已启动: {self.channel_server.host}:{self.channel_server.port}")
            except Exception as e:
                print(f"[警告] 频道服务器启动失败: {e}")
        
        # 启动游戏服务器
        if self.game_server:
            try:
                self.game_server.start()
                print(f"[Server] 游戏服务器已启动（{len(self.game_server.channels)}个频道）")
            except Exception as e:
                print(f"[警告] 游戏服务器启动失败: {e}")
        
        # 启动HTTP管理服务器
        if self.admin_server:
            if not self.admin_server.start():
                print("[警告] HTTP管理服务器启动失败，继续启动...")
            else:
                print(f"[Server] HTTP管理服务已启动: {self.admin_server.host}:{self.admin_server.port}")
        
        self.running = True
        self.start_time = time.time()
        
        print("\n" + "=" * 60)
        print("服务端启动成功！")
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"当前连接数: {self.network_manager.get_total_connections()}")
        print("按 Ctrl+C 停止服务端")
        print("=" * 60)
        
        self.logger.info("服务端启动成功")
        
        # 主循环
        try:
            while self.running:
                time.sleep(1)
                
                # 定期清理过期会话
                if int(time.time()) % 300 == 0:  # 每5分钟
                    self.account_manager.cleanup_expired_sessions()
                    
        except KeyboardInterrupt:
            print("\n[Server] 收到中断信号，正在停止...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """停止服务端"""
        if not self.running:
            return
        
        print("\n[Server] 正在停止服务端...")
        self.logger.info("正在停止服务端...")
        
        self.running = False
        
        # 停止网络服务
        if self.network_manager:
            self.network_manager.stop()
        
        # 停止频道服务器
        if self.channel_server:
            try:
                self.channel_server.stop()
                print("[Server] 频道服务器已停止")
            except Exception as e:
                print(f"[警告] 频道服务器停止失败: {e}")
        
        # 停止游戏服务器
        if self.game_server:
            try:
                self.game_server.stop()
                print("[Server] 游戏服务器已停止")
            except Exception as e:
                print(f"[警告] 游戏服务器停止失败: {e}")
        
        # 停止HTTP管理服务器
        if self.admin_server:
            self.admin_server.stop()
        
        # 停止所有进程
        if self.process_manager:
            self.process_manager.stop_all()
        
        # 停止便携版MySQL
        if self.mysql_manager:
            print("\n[Server] 正在停止便携版MySQL...")
            success, msg = self.mysql_manager.stop(wait_timeout=10)
            if success:
                print(f"[Server] MySQL已停止: {msg}")
            else:
                print(f"[Server] MySQL停止失败: {msg}")
        
        # 关闭数据库
        if self.db_manager:
            self.db_manager.close()
        
        # 关闭PVF
        if self.pvf_manager:
            self.pvf_manager.close()
        
        # 关闭日志
        if self.logger:
            self.logger.info("服务端已停止")
            self.logger.close()
        
        uptime = time.time() - self.start_time if self.start_time else 0
        print(f"\n[Server] 服务端已停止，运行时间: {uptime:.1f} 秒")
        print("=" * 60)
    
    def get_status(self) -> dict:
        """获取服务端状态"""
        return {
            'version': self.version,
            'running': self.running,
            'uptime': time.time() - self.start_time if self.start_time else 0,
            'database_mode': self.config_manager.config.database.mode if self.config_manager else 'unknown',
            'total_connections': self.network_manager.get_total_connections() if self.network_manager else 0,
            'online_accounts': self.account_manager.get_online_count() if self.account_manager else 0,
            'channel_server_running': self.channel_server.running if self.channel_server else False,
            'game_server_running': self.game_server.running if self.game_server else False,
            'game_sessions': len(self.game_server.sessions) if self.game_server else 0,
            'character_count': self.character_manager.repository.count() if self.character_manager else 0,
        }


def main():
    """主函数"""
    try:
        parser = argparse.ArgumentParser(description='GameServer 服务端 Python 实现')
        parser.add_argument('-c', '--config', type=str, default='', help='配置文件路径')
        parser.add_argument('-v', '--version', action='store_true', help='显示版本信息')
        parser.add_argument('--debug', action='store_true', help='调试模式')
        
        args = parser.parse_args()
        
        if args.version:
            print(f"GameServer 服务端 Python 实现 v0.1.0")
            print(f"基于 DNF90-external-oneclick 服务端架构")
            print(f"作者: ereshkigal996")
            return
        
        print("=" * 60)
        print(f"GameServer 服务端 Python 实现 v0.1.0")
        print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 创建服务端实例
        server = GameServer()
        
        # 初始化
        if not server.init(args.config):
            print("[错误] 服务端初始化失败")
            sys.exit(1)
        
        # 启动
        if not server.start():
            print("[错误] 服务端启动失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"[致命错误] 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
