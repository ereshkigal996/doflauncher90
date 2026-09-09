"""
配置管理模块
负责解析和管理 instance.json 配置文件
"""

import json
import os
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class ServerConfig:
    """服务端配置"""
    advertise_ip: str = "AUTO_DETECT"
    channel_listen: str = "127.0.0.1:7001"
    admin_listen: str = "127.0.0.1:18111"
    admin_token: str = ""
    account_id: str = ""
    packet_log: bool = True
    debug_mode: bool = False
    debug_strike_on_skill_use: bool = False
    party_udp_relay_enabled: bool = True
    party_udp_relay_port_start: int = 30000
    party_udp_relay_port_count: int = 64


@dataclass
class DatabaseConfig:
    """数据库配置"""
    mode: str = "mysql"  # sqlite / mysql
    path: str = "data/dnf90.db"
    host: str = "127.0.0.1"
    port: int = 13306
    name: str = "dnf_local"
    user: str = "root"
    password: str = ""


@dataclass
class GameConfig:
    """游戏配置"""
    shard_id: str = "9999"
    pvf_path: str = "data/dnf/Script.pvf"
    pvf_max_bytes: int = -1
    channel_info_path: str = "data/dnf/channel_info.etc"


@dataclass
class ProtocolConfig:
    """协议配置"""
    profile: str = "90cn-decode-bypass-v1"
    game_upper_header: str = "server16"
    game_upper_body_codec: str = "plaintext"
    game_upper_client_body_codec: str = "plaintext"
    game_outer_token: str = ""
    channel_server_index: int = 1
    channel_advertise_server_index: int = 1
    region_id: int = 1
    region_name: str = ""


@dataclass
class ClientConfig:
    """客户端配置"""
    directory: str = ""
    initial_game_port: int = 0
    hook_create: bool = True


@dataclass
class InstanceConfig:
    """实例配置（对应 instance.json）"""
    schema_version: int = 1
    installation_id: str = ""
    mode: str = "local-single-account"
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    game: GameConfig = field(default_factory=GameConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    client: ClientConfig = field(default_factory=ClientConfig)
    
    # 原始JSON数据
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # 配置文件路径和SHA256
    config_path: str = ""
    config_sha256: str = ""


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = ""):
        self.config_path = config_path
        self.config = InstanceConfig()
        self._loaded = False
    
    def load(self, config_path: str = "") -> bool:
        """加载配置文件"""
        if config_path:
            self.config_path = config_path
        
        if not self.config_path or not os.path.exists(self.config_path):
            print(f"[ConfigManager] 配置文件不存在: {self.config_path}")
            return False
        
        try:
            # 使用utf-8-sig编码，自动处理UTF-8 BOM
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                data = json.load(f)
            
            self._parse_config(data)
            self.config.raw_data = data
            self.config.config_path = self.config_path
            
            # 计算配置文件SHA256
            self.config.config_sha256 = self._calculate_sha256(self.config_path)
            
            self._loaded = True
            print(f"[ConfigManager] 配置加载成功: {self.config_path}")
            print(f"[ConfigManager] 安装ID: {self.config.installation_id}")
            print(f"[ConfigManager] 数据库模式: {self.config.database.mode}")
            print(f"[ConfigManager] 频道监听: {self.config.server.channel_listen}")
            return True
            
        except Exception as e:
            print(f"[ConfigManager] 配置加载失败: {e}")
            return False
    
    def _parse_config(self, data: Dict[str, Any]):
        """解析配置数据"""
        # 基础配置
        self.config.schema_version = data.get('schemaVersion', 1)
        self.config.installation_id = data.get('installationId', '')
        self.config.mode = data.get('mode', 'local-single-account')
        
        # 服务端配置
        server_data = data.get('server', {})
        self.config.server = ServerConfig(
            advertise_ip=server_data.get('advertiseIp', 'AUTO_DETECT'),
            channel_listen=server_data.get('channelListen', '127.0.0.1:7001'),
            admin_listen=server_data.get('adminListen', '127.0.0.1:18111'),
            admin_token=server_data.get('adminToken', ''),
            account_id=server_data.get('accountId', ''),
            packet_log=server_data.get('packetLog', True),
            debug_mode=server_data.get('debugMode', False),
            debug_strike_on_skill_use=server_data.get('debugStrikeOnSkillUse', False),
            party_udp_relay_enabled=server_data.get('partyUdpRelayEnabled', True),
            party_udp_relay_port_start=server_data.get('partyUdpRelayPortStart', 30000),
            party_udp_relay_port_count=server_data.get('partyUdpRelayPortCount', 64),
        )
        
        # 数据库配置
        db_data = data.get('database', {})
        self.config.database = DatabaseConfig(
            mode=db_data.get('mode', 'sqlite'),
            path=db_data.get('path', 'data/dnf90.db'),
            host=db_data.get('host', '127.0.0.1'),
            port=db_data.get('port', 13306),
            name=db_data.get('name', 'dnf_local'),
            user=db_data.get('user', 'root'),
            password=db_data.get('password', ''),
        )
        
        # 游戏配置
        game_data = data.get('game', {})
        self.config.game = GameConfig(
            shard_id=game_data.get('shardId', '9999'),
            pvf_path=game_data.get('pvfPath', 'data/dnf/Script.pvf'),
            pvf_max_bytes=game_data.get('pvfMaxBytes', -1),
            channel_info_path=game_data.get('channelInfoPath', 'data/dnf/channel_info.etc'),
        )
        
        # 协议配置
        proto_data = data.get('protocol', {})
        self.config.protocol = ProtocolConfig(
            profile=proto_data.get('profile', '90cn-decode-bypass-v1'),
            game_upper_header=proto_data.get('gameUpperHeader', 'server16'),
            game_upper_body_codec=proto_data.get('gameUpperBodyCodec', 'plaintext'),
            game_upper_client_body_codec=proto_data.get('gameUpperClientBodyCodec', 'plaintext'),
            game_outer_token=proto_data.get('gameOuterToken', ''),
            channel_server_index=proto_data.get('channelServerIndex', 1),
            channel_advertise_server_index=proto_data.get('channelAdvertiseServerIndex', 1),
            region_id=proto_data.get('regionId', 1),
            region_name=proto_data.get('regionName', ''),
        )
        
        # 客户端配置
        client_data = data.get('client', {})
        self.config.client = ClientConfig(
            directory=client_data.get('directory', ''),
            initial_game_port=client_data.get('initialGamePort', 0),
            hook_create=client_data.get('hookCreate', True),
        )
    
    def _calculate_sha256(self, file_path: str) -> str:
        """计算文件SHA256"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            print(f"[ConfigManager] SHA256计算失败: {e}")
            return ""
    
    def save(self, output_path: str = "") -> bool:
        """保存配置到文件"""
        if not output_path:
            output_path = self.config_path
        
        try:
            # 从dataclass转换为dict
            data = {
                'schemaVersion': self.config.schema_version,
                'installationId': self.config.installation_id,
                'mode': self.config.mode,
                'server': {
                    'advertiseIp': self.config.server.advertise_ip,
                    'channelListen': self.config.server.channel_listen,
                    'adminListen': self.config.server.admin_listen,
                    'adminToken': self.config.server.admin_token,
                    'accountId': self.config.server.account_id,
                    'packetLog': self.config.server.packet_log,
                    'debugMode': self.config.server.debug_mode,
                    'debugStrikeOnSkillUse': self.config.server.debug_strike_on_skill_use,
                    'partyUdpRelayEnabled': self.config.server.party_udp_relay_enabled,
                    'partyUdpRelayPortStart': self.config.server.party_udp_relay_port_start,
                    'partyUdpRelayPortCount': self.config.server.party_udp_relay_port_count,
                },
                'database': {
                    'mode': self.config.database.mode,
                    'path': self.config.database.path,
                    'host': self.config.database.host,
                    'port': self.config.database.port,
                    'name': self.config.database.name,
                    'user': self.config.database.user,
                    'password': self.config.database.password,
                },
                'game': {
                    'shardId': self.config.game.shard_id,
                    'pvfPath': self.config.game.pvf_path,
                    'pvfMaxBytes': self.config.game.pvf_max_bytes,
                    'channelInfoPath': self.config.game.channel_info_path,
                },
                'protocol': {
                    'profile': self.config.protocol.profile,
                    'gameUpperHeader': self.config.protocol.game_upper_header,
                    'gameUpperBodyCodec': self.config.protocol.game_upper_body_codec,
                    'gameUpperClientBodyCodec': self.config.protocol.game_upper_client_body_codec,
                    'gameOuterToken': self.config.protocol.game_outer_token,
                    'channelServerIndex': self.config.protocol.channel_server_index,
                    'channelAdvertiseServerIndex': self.config.protocol.channel_advertise_server_index,
                    'regionId': self.config.protocol.region_id,
                    'regionName': self.config.protocol.region_name,
                },
                'client': {
                    'directory': self.config.client.directory,
                    'initialGamePort': self.config.client.initial_game_port,
                    'hookCreate': self.config.client.hook_create,
                },
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"[ConfigManager] 配置保存成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[ConfigManager] 配置保存失败: {e}")
            return False
    
    def get_mysql_dsn(self) -> str:
        """获取MySQL DSN连接字符串"""
        db = self.config.database
        return f"{db.user}:{db.password}@tcp({db.host}:{db.port})/{db.name}?parseTime=true&charset=utf8mb4,utf8"
    
    def is_loaded(self) -> bool:
        """配置是否已加载"""
        return self._loaded


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config(config_path: str) -> bool:
    """初始化全局配置"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager.load()
