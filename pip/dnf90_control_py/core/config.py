# -*- coding: utf-8 -*-
"""
配置管理模块
对应Go版 config.go / instance.go
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List


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
    party_udp_relay_enabled: bool = True
    party_udp_relay_port_start: int = 30000
    party_udp_relay_port_count: int = 64


@dataclass
class DatabaseConfig:
    """数据库配置"""
    mode: str = "portable"  # portable / sqlite
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
    dungeon_batch_pickup_enabled: bool = True


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
    """实例配置（对应instance.json）"""
    schema_version: int = 1
    installation_id: str = ""
    mode: str = "local-single-account"
    server: ServerConfig = field(default_factory=ServerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    game: GameConfig = field(default_factory=GameConfig)
    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    client: ClientConfig = field(default_factory=ClientConfig)
    raw: Dict[str, Any] = field(default_factory=dict)


def load_instance_config(config_path: str) -> tuple[Optional[InstanceConfig], Optional[str]]:
    """
    加载实例配置
    对应Go版 instance.go
    """
    if not os.path.isfile(config_path):
        return None, f"config file not found: {config_path}"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in config: {e}"
    except Exception as e:
        return None, f"read config failed: {e}"
    
    config = InstanceConfig()
    config.raw = data
    
    # 基础字段
    config.schema_version = data.get("schemaVersion", 1)
    config.installation_id = data.get("installationId", "")
    config.mode = data.get("mode", "local-single-account")
    
    # server
    server_data = data.get("server", {})
    config.server.advertise_ip = server_data.get("advertiseIp", "AUTO_DETECT")
    config.server.channel_listen = server_data.get("channelListen", "127.0.0.1:7001")
    config.server.admin_listen = server_data.get("adminListen", "127.0.0.1:18111")
    config.server.admin_token = server_data.get("adminToken", "")
    config.server.account_id = server_data.get("accountId", "")
    config.server.packet_log = server_data.get("packetLog", True)
    config.server.debug_mode = server_data.get("debugMode", False)
    config.server.party_udp_relay_enabled = server_data.get("partyUdpRelayEnabled", True)
    config.server.party_udp_relay_port_start = server_data.get("partyUdpRelayPortStart", 30000)
    config.server.party_udp_relay_port_count = server_data.get("partyUdpRelayPortCount", 64)
    
    # database
    db_data = data.get("database", {})
    config.database.mode = db_data.get("mode", "portable")
    config.database.path = db_data.get("path", "data/dnf90.db")
    config.database.host = db_data.get("host", "127.0.0.1")
    config.database.port = db_data.get("port", 13306)
    config.database.name = db_data.get("name", "dnf_local")
    config.database.user = db_data.get("user", "root")
    config.database.password = db_data.get("password", "")
    
    # game
    game_data = data.get("game", {})
    config.game.shard_id = game_data.get("shardId", "9999")
    config.game.pvf_path = game_data.get("pvfPath", "data/dnf/Script.pvf")
    config.game.pvf_max_bytes = game_data.get("pvfMaxBytes", -1)
    config.game.channel_info_path = game_data.get("channelInfoPath", "data/dnf/channel_info.etc")
    config.game.dungeon_batch_pickup_enabled = game_data.get("dungeonBatchPickupEnabled", True)
    
    # protocol
    proto_data = data.get("protocol", {})
    config.protocol.profile = proto_data.get("profile", "90cn-decode-bypass-v1")
    config.protocol.game_upper_header = proto_data.get("gameUpperHeader", "server16")
    config.protocol.game_upper_body_codec = proto_data.get("gameUpperBodyCodec", "plaintext")
    config.protocol.game_upper_client_body_codec = proto_data.get("gameUpperClientBodyCodec", "plaintext")
    config.protocol.game_outer_token = proto_data.get("gameOuterToken", "")
    config.protocol.channel_server_index = proto_data.get("channelServerIndex", 1)
    config.protocol.channel_advertise_server_index = proto_data.get("channelAdvertiseServerIndex", 1)
    config.protocol.region_id = proto_data.get("regionId", 1)
    config.protocol.region_name = proto_data.get("regionName", "")
    
    # client
    client_data = data.get("client", {})
    config.client.directory = client_data.get("directory", "")
    config.client.initial_game_port = client_data.get("initialGamePort", 0)
    config.client.hook_create = client_data.get("hookCreate", True)
    
    return config, None


def save_instance_config(config_path: str, config: InstanceConfig) -> tuple[bool, Optional[str]]:
    """保存实例配置"""
    try:
        data = {
            "schemaVersion": config.schema_version,
            "installationId": config.installation_id,
            "mode": config.mode,
            "server": {
                "advertiseIp": config.server.advertise_ip,
                "channelListen": config.server.channel_listen,
                "adminListen": config.server.admin_listen,
                "adminToken": config.server.admin_token,
                "accountId": config.server.account_id,
                "packetLog": config.server.packet_log,
                "debugMode": config.server.debug_mode,
                "partyUdpRelayEnabled": config.server.party_udp_relay_enabled,
                "partyUdpRelayPortStart": config.server.party_udp_relay_port_start,
                "partyUdpRelayPortCount": config.server.party_udp_relay_port_count,
            },
            "database": {
                "mode": config.database.mode,
                "path": config.database.path,
                "host": config.database.host,
                "port": config.database.port,
                "name": config.database.name,
                "user": config.database.user,
                "password": config.database.password,
            },
            "game": {
                "shardId": config.game.shard_id,
                "pvfPath": config.game.pvf_path,
                "pvfMaxBytes": config.game.pvf_max_bytes,
                "channelInfoPath": config.game.channel_info_path,
                "dungeonBatchPickupEnabled": config.game.dungeon_batch_pickup_enabled,
            },
            "protocol": {
                "profile": config.protocol.profile,
                "gameUpperHeader": config.protocol.game_upper_header,
                "gameUpperBodyCodec": config.protocol.game_upper_body_codec,
                "gameUpperClientBodyCodec": config.protocol.game_upper_client_body_codec,
                "gameOuterToken": config.protocol.game_outer_token,
                "channelServerIndex": config.protocol.channel_server_index,
                "channelAdvertiseServerIndex": config.protocol.channel_advertise_server_index,
                "regionId": config.protocol.region_id,
                "regionName": config.protocol.region_name,
            },
            "client": {
                "directory": config.client.directory,
                "initialGamePort": config.client.initial_game_port,
                "hookCreate": config.client.hook_create,
            },
        }
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, None
    except Exception as e:
        return False, f"save config failed: {e}"
