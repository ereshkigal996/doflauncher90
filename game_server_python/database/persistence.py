"""
数据持久化模块
实现角色、物品、技能、邮件等游戏数据的数据库存储和加载
"""

import json
import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import asdict

from database.db_manager import DatabaseManager, get_db_manager


# 日志
logger = logging.getLogger(__name__)


class DataPersistence:
    """数据持久化管理器"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据持久化管理器
        
        Args:
            db_manager: 数据库管理器（为None时使用全局实例）
        """
        self.db = db_manager or get_db_manager()
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        初始化数据库表结构
        
        Returns:
            是否成功
        """
        if self._initialized:
            return True
        
        try:
            self._create_tables()
            self._initialized = True
            logger.info("数据持久化模块初始化成功")
            return True
        except Exception as e:
            logger.error(f"数据持久化模块初始化失败: {e}")
            return False
    
    def _create_tables(self):
        """创建数据库表"""
        tables = [
            # 角色表
            """
            CREATE TABLE IF NOT EXISTS dnf_characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id VARCHAR(64) NOT NULL,
                name VARCHAR(32) NOT NULL,
                job VARCHAR(32) DEFAULT '',
                grow_type INTEGER DEFAULT 0,
                level INTEGER DEFAULT 1,
                exp INTEGER DEFAULT 0,
                slot_index INTEGER DEFAULT 0,
                town_id INTEGER DEFAULT 2,
                position_x REAL DEFAULT 0,
                position_y REAL DEFAULT 0,
                strength INTEGER DEFAULT 10,
                intelligence INTEGER DEFAULT 10,
                vitality INTEGER DEFAULT 10,
                spirit INTEGER DEFAULT 10,
                hp_max INTEGER DEFAULT 1000,
                mp_max INTEGER DEFAULT 500,
                physical_attack INTEGER DEFAULT 100,
                magical_attack INTEGER DEFAULT 100,
                physical_defense INTEGER DEFAULT 100,
                magical_defense INTEGER DEFAULT 100,
                attack_speed INTEGER DEFAULT 1000,
                move_speed INTEGER DEFAULT 1000,
                cast_speed INTEGER DEFAULT 1000,
                fatigue_used INTEGER DEFAULT 0,
                fatigue_limit INTEGER DEFAULT 156,
                fatigue_battery INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                cera INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(account_id, slot_index)
            )
            """,
            
            # 背包物品表
            """
            CREATE TABLE IF NOT EXISTS dnf_inventory_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                inventory_type INTEGER DEFAULT 0,
                slot_index INTEGER DEFAULT 0,
                item_id INTEGER DEFAULT 0,
                item_name VARCHAR(128) DEFAULT '',
                item_type VARCHAR(32) DEFAULT '',
                count INTEGER DEFAULT 0,
                reinforce_level INTEGER DEFAULT 0,
                amplify_level INTEGER DEFAULT 0,
                amplify_type VARCHAR(16) DEFAULT '',
                enchant_card_id INTEGER DEFAULT 0,
                enchant_name VARCHAR(64) DEFAULT '',
                quality INTEGER DEFAULT 100,
                durability INTEGER DEFAULT 100,
                max_durability INTEGER DEFAULT 100,
                sealed INTEGER DEFAULT 0,
                expire_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                FOREIGN KEY (character_id) REFERENCES dnf_characters(id) ON DELETE CASCADE
            )
            """,
            
            # 已装备物品表
            """
            CREATE TABLE IF NOT EXISTS dnf_equipped_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                equip_slot INTEGER DEFAULT 0,
                item_id INTEGER DEFAULT 0,
                item_name VARCHAR(128) DEFAULT '',
                reinforce_level INTEGER DEFAULT 0,
                amplify_level INTEGER DEFAULT 0,
                amplify_type VARCHAR(16) DEFAULT '',
                enchant_card_id INTEGER DEFAULT 0,
                enchant_name VARCHAR(64) DEFAULT '',
                quality INTEGER DEFAULT 100,
                durability INTEGER DEFAULT 100,
                max_durability INTEGER DEFAULT 100,
                sealed INTEGER DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                created_at REAL DEFAULT 0,
                UNIQUE(character_id, equip_slot),
                FOREIGN KEY (character_id) REFERENCES dnf_characters(id) ON DELETE CASCADE
            )
            """,
            
            # 技能表
            """
            CREATE TABLE IF NOT EXISTS dnf_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL,
                skill_id INTEGER DEFAULT 0,
                skill_name VARCHAR(64) DEFAULT '',
                level INTEGER DEFAULT 1,
                quick_slot INTEGER DEFAULT -1,
                learn_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(character_id, skill_id),
                FOREIGN KEY (character_id) REFERENCES dnf_characters(id) ON DELETE CASCADE
            )
            """,
            
            # 技能点表
            """
            CREATE TABLE IF NOT EXISTS dnf_skill_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER NOT NULL UNIQUE,
                current_points INTEGER DEFAULT 0,
                max_points INTEGER DEFAULT 0,
                updated_at REAL DEFAULT 0,
                FOREIGN KEY (character_id) REFERENCES dnf_characters(id) ON DELETE CASCADE
            )
            """,
            
            # 邮件表
            """
            CREATE TABLE IF NOT EXISTS dnf_mails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mail_id INTEGER DEFAULT 0,
                mail_type INTEGER DEFAULT 0,
                status INTEGER DEFAULT 0,
                sender_id VARCHAR(64) DEFAULT '',
                sender_name VARCHAR(32) DEFAULT '',
                receiver_id VARCHAR(64) NOT NULL,
                receiver_name VARCHAR(32) DEFAULT '',
                title VARCHAR(128) DEFAULT '',
                content TEXT DEFAULT '',
                attachment_item_id INTEGER DEFAULT 0,
                attachment_item_name VARCHAR(128) DEFAULT '',
                attachment_count INTEGER DEFAULT 0,
                attachment_reinforce INTEGER DEFAULT 0,
                attachment_amplify INTEGER DEFAULT 0,
                attachment_amplify_type VARCHAR(16) DEFAULT '',
                attachment_gold INTEGER DEFAULT 0,
                attachment_cera INTEGER DEFAULT 0,
                send_time REAL DEFAULT 0,
                read_time REAL DEFAULT 0,
                delete_time REAL DEFAULT 0,
                expire_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(mail_id)
            )
            """,
            
            # 账号表
            """
            CREATE TABLE IF NOT EXISTS dnf_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(64) NOT NULL UNIQUE,
                password VARCHAR(256) DEFAULT '',
                cera INTEGER DEFAULT 0,
                gold INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0,
                last_login_at REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}'
            )
            """,
            
            # 副本通关记录表
            """
            CREATE TABLE IF NOT EXISTS dnf_dungeon_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id VARCHAR(64) NOT NULL,
                dungeon_id INTEGER DEFAULT 0,
                dungeon_name VARCHAR(64) DEFAULT '',
                difficulty INTEGER DEFAULT 0,
                clear_time REAL DEFAULT 0,
                rank VARCHAR(8) DEFAULT '',
                exp_reward INTEGER DEFAULT 0,
                gold_reward INTEGER DEFAULT 0,
                items_reward TEXT DEFAULT '[]',
                clear_count INTEGER DEFAULT 1,
                first_clear INTEGER DEFAULT 0,
                created_at REAL DEFAULT 0,
                updated_at REAL DEFAULT 0,
                UNIQUE(character_id, dungeon_id, difficulty)
            )
            """,
            
            # 拍卖行上架记录表
            """
            CREATE TABLE IF NOT EXISTS dnf_auction_listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id INTEGER DEFAULT 0,
                seller_id VARCHAR(64) NOT NULL,
                seller_name VARCHAR(32) DEFAULT '',
                item_id INTEGER DEFAULT 0,
                item_name VARCHAR(128) DEFAULT '',
                item_type VARCHAR(32) DEFAULT '',
                item_level INTEGER DEFAULT 0,
                rarity INTEGER DEFAULT 0,
                quantity INTEGER DEFAULT 1,
                reinforce_level INTEGER DEFAULT 0,
                amplify_level INTEGER DEFAULT 0,
                amplify_type VARCHAR(16) DEFAULT '',
                price INTEGER DEFAULT 0,
                unit_price INTEGER DEFAULT 0,
                status INTEGER DEFAULT 0,
                list_time REAL DEFAULT 0,
                expire_time REAL DEFAULT 0,
                sold_time REAL DEFAULT 0,
                cancel_time REAL DEFAULT 0,
                buyer_id VARCHAR(64) DEFAULT '',
                buyer_name VARCHAR(32) DEFAULT '',
                deposit_fee INTEGER DEFAULT 0,
                transaction_fee INTEGER DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(listing_id)
            )
            """,
            
            # 拍卖行交易记录表
            """
            CREATE TABLE IF NOT EXISTS dnf_auction_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER DEFAULT 0,
                listing_id INTEGER DEFAULT 0,
                item_id INTEGER DEFAULT 0,
                item_name VARCHAR(128) DEFAULT '',
                quantity INTEGER DEFAULT 1,
                price INTEGER DEFAULT 0,
                transaction_fee INTEGER DEFAULT 0,
                seller_income INTEGER DEFAULT 0,
                seller_id VARCHAR(64) DEFAULT '',
                seller_name VARCHAR(32) DEFAULT '',
                buyer_id VARCHAR(64) DEFAULT '',
                buyer_name VARCHAR(32) DEFAULT '',
                transaction_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(transaction_id)
            )
            """,
            
            # 公会表
            """
            CREATE TABLE IF NOT EXISTS dnf_guilds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER DEFAULT 0,
                guild_name VARCHAR(32) NOT NULL UNIQUE,
                guild_notice TEXT DEFAULT '',
                guild_introduction TEXT DEFAULT '',
                master_id VARCHAR(64) NOT NULL,
                master_name VARCHAR(32) DEFAULT '',
                level INTEGER DEFAULT 1,
                max_level INTEGER DEFAULT 10,
                exp INTEGER DEFAULT 0,
                exp_to_next_level INTEGER DEFAULT 100000,
                funds INTEGER DEFAULT 0,
                member_count INTEGER DEFAULT 0,
                max_members INTEGER DEFAULT 100,
                emblem_id INTEGER DEFAULT 0,
                create_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(guild_id)
            )
            """,
            
            # 公会成员表
            """
            CREATE TABLE IF NOT EXISTS dnf_guild_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER DEFAULT 0,
                character_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(32) DEFAULT '',
                account_id VARCHAR(64) DEFAULT '',
                rank INTEGER DEFAULT 4,
                level INTEGER DEFAULT 1,
                job VARCHAR(32) DEFAULT '',
                contribution INTEGER DEFAULT 0,
                weekly_contribution INTEGER DEFAULT 0,
                is_online INTEGER DEFAULT 0,
                last_login_time REAL DEFAULT 0,
                join_time REAL DEFAULT 0,
                rank_change_time REAL DEFAULT 0,
                extra_data TEXT DEFAULT '{}',
                UNIQUE(character_id),
                FOREIGN KEY (guild_id) REFERENCES dnf_guilds(guild_id) ON DELETE CASCADE
            )
            """,
            
            # 公会申请表
            """
            CREATE TABLE IF NOT EXISTS dnf_guild_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER DEFAULT 0,
                guild_id INTEGER DEFAULT 0,
                character_id VARCHAR(64) NOT NULL,
                character_name VARCHAR(32) DEFAULT '',
                account_id VARCHAR(64) DEFAULT '',
                status INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                level INTEGER DEFAULT 1,
                job VARCHAR(32) DEFAULT '',
                apply_time REAL DEFAULT 0,
                process_time REAL DEFAULT 0,
                processed_by VARCHAR(64) DEFAULT '',
                extra_data TEXT DEFAULT '{}',
                UNIQUE(application_id)
            )
            """,
        ]
        
        for sql in tables:
            self.db.execute(sql)
        
        logger.info("数据库表结构创建完成")
    
    # ========== 角色持久化 ==========
    
    def save_character(self, character_data: Dict[str, Any]) -> Optional[int]:
        """
        保存角色数据
        
        Args:
            character_data: 角色数据字典
            
        Returns:
            角色ID（失败返回None）
        """
        try:
            now = time.time()
            
            # 检查是否已存在
            existing = self.db.query_one(
                "SELECT id FROM dnf_characters WHERE account_id = ? AND slot_index = ?",
                (character_data.get('account_id', ''), character_data.get('slot_index', 0))
            )
            
            extra_data = json.dumps(character_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                # 更新
                self.db.execute("""
                    UPDATE dnf_characters SET
                        name = ?, job = ?, grow_type = ?, level = ?, exp = ?,
                        town_id = ?, position_x = ?, position_y = ?,
                        strength = ?, intelligence = ?, vitality = ?, spirit = ?,
                        hp_max = ?, mp_max = ?, physical_attack = ?, magical_attack = ?,
                        physical_defense = ?, magical_defense = ?,
                        attack_speed = ?, move_speed = ?, cast_speed = ?,
                        fatigue_used = ?, fatigue_limit = ?, fatigue_battery = ?,
                        gold = ?, cera = ?, updated_at = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    character_data.get('name', ''),
                    character_data.get('job', ''),
                    character_data.get('grow_type', 0),
                    character_data.get('level', 1),
                    character_data.get('exp', 0),
                    character_data.get('town_id', 2),
                    character_data.get('position_x', 0.0),
                    character_data.get('position_y', 0.0),
                    character_data.get('strength', 10),
                    character_data.get('intelligence', 10),
                    character_data.get('vitality', 10),
                    character_data.get('spirit', 10),
                    character_data.get('hp_max', 1000),
                    character_data.get('mp_max', 500),
                    character_data.get('physical_attack', 100),
                    character_data.get('magical_attack', 100),
                    character_data.get('physical_defense', 100),
                    character_data.get('magical_defense', 100),
                    character_data.get('attack_speed', 1000),
                    character_data.get('move_speed', 1000),
                    character_data.get('cast_speed', 1000),
                    character_data.get('fatigue_used', 0),
                    character_data.get('fatigue_limit', 156),
                    character_data.get('fatigue_battery', 0),
                    character_data.get('gold', 0),
                    character_data.get('cera', 0),
                    now,
                    extra_data,
                    existing['id'],
                ))
                return existing['id']
            else:
                # 新建
                self.db.execute("""
                    INSERT INTO dnf_characters (
                        account_id, name, job, grow_type, level, exp, slot_index,
                        town_id, position_x, position_y,
                        strength, intelligence, vitality, spirit,
                        hp_max, mp_max, physical_attack, magical_attack,
                        physical_defense, magical_defense,
                        attack_speed, move_speed, cast_speed,
                        fatigue_used, fatigue_limit, fatigue_battery,
                        gold, cera, created_at, updated_at, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    character_data.get('account_id', ''),
                    character_data.get('name', ''),
                    character_data.get('job', ''),
                    character_data.get('grow_type', 0),
                    character_data.get('level', 1),
                    character_data.get('exp', 0),
                    character_data.get('slot_index', 0),
                    character_data.get('town_id', 2),
                    character_data.get('position_x', 0.0),
                    character_data.get('position_y', 0.0),
                    character_data.get('strength', 10),
                    character_data.get('intelligence', 10),
                    character_data.get('vitality', 10),
                    character_data.get('spirit', 10),
                    character_data.get('hp_max', 1000),
                    character_data.get('mp_max', 500),
                    character_data.get('physical_attack', 100),
                    character_data.get('magical_attack', 100),
                    character_data.get('physical_defense', 100),
                    character_data.get('magical_defense', 100),
                    character_data.get('attack_speed', 1000),
                    character_data.get('move_speed', 1000),
                    character_data.get('cast_speed', 1000),
                    character_data.get('fatigue_used', 0),
                    character_data.get('fatigue_limit', 156),
                    character_data.get('fatigue_battery', 0),
                    character_data.get('gold', 0),
                    character_data.get('cera', 0),
                    now,
                    now,
                    extra_data,
                ))
                
                # 获取新ID
                result = self.db.query_one(
                    "SELECT id FROM dnf_characters WHERE account_id = ? AND slot_index = ?",
                    (character_data.get('account_id', ''), character_data.get('slot_index', 0))
                )
                return result['id'] if result else None
                
        except Exception as e:
            logger.error(f"保存角色失败: {e}")
            return None
    
    def load_character(self, character_id: int) -> Optional[Dict[str, Any]]:
        """
        加载角色数据
        
        Args:
            character_id: 角色ID
            
        Returns:
            角色数据字典
        """
        try:
            result = self.db.query_one(
                "SELECT * FROM dnf_characters WHERE id = ?",
                (character_id,)
            )
            if not result:
                return None
            
            # 解析extra_data
            if result.get('extra_data'):
                try:
                    result['extra_data'] = json.loads(result['extra_data'])
                except:
                    result['extra_data'] = {}
            
            return result
        except Exception as e:
            logger.error(f"加载角色失败: {e}")
            return None
    
    def load_characters_by_account(self, account_id: str) -> List[Dict[str, Any]]:
        """
        加载账号下所有角色
        
        Args:
            account_id: 账号ID
            
        Returns:
            角色列表
        """
        try:
            results = self.db.query(
                "SELECT * FROM dnf_characters WHERE account_id = ? ORDER BY slot_index",
                (account_id,)
            )
            
            for result in results:
                if result.get('extra_data'):
                    try:
                        result['extra_data'] = json.loads(result['extra_data'])
                    except:
                        result['extra_data'] = {}
            
            return results
        except Exception as e:
            logger.error(f"加载角色列表失败: {e}")
            return []
    
    def delete_character(self, character_id: int) -> bool:
        """
        删除角色
        
        Args:
            character_id: 角色ID
            
        Returns:
            是否成功
        """
        try:
            # 级联删除相关数据
            self.db.execute("DELETE FROM dnf_inventory_items WHERE character_id = ?", (character_id,))
            self.db.execute("DELETE FROM dnf_equipped_items WHERE character_id = ?", (character_id,))
            self.db.execute("DELETE FROM dnf_skills WHERE character_id = ?", (character_id,))
            self.db.execute("DELETE FROM dnf_skill_points WHERE character_id = ?", (character_id,))
            self.db.execute("DELETE FROM dnf_characters WHERE id = ?", (character_id,))
            return True
        except Exception as e:
            logger.error(f"删除角色失败: {e}")
            return False
    
    # ========== 背包持久化 ==========
    
    def save_inventory(self, character_id: int, inventory_data: List[Dict[str, Any]]) -> bool:
        """
        保存背包数据
        
        Args:
            character_id: 角色ID
            inventory_data: 背包物品列表
            
        Returns:
            是否成功
        """
        try:
            # 先清空旧数据
            self.db.execute(
                "DELETE FROM dnf_inventory_items WHERE character_id = ?",
                (character_id,)
            )
            
            # 插入新数据
            for item in inventory_data:
                if item.get('item_id', 0) == 0 or item.get('count', 0) <= 0:
                    continue
                
                extra_data = json.dumps(item.get('extra_data', {}), ensure_ascii=False)
                
                self.db.execute("""
                    INSERT INTO dnf_inventory_items (
                        character_id, inventory_type, slot_index, item_id, item_name, item_type,
                        count, reinforce_level, amplify_level, amplify_type,
                        enchant_card_id, enchant_name, quality, durability, max_durability,
                        sealed, expire_time, extra_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    character_id,
                    item.get('inventory_type', 0),
                    item.get('slot_index', 0),
                    item.get('item_id', 0),
                    item.get('item_name', ''),
                    item.get('item_type', ''),
                    item.get('count', 0),
                    item.get('reinforce_level', 0),
                    item.get('amplify_level', 0),
                    item.get('amplify_type', ''),
                    item.get('enchant_card_id', 0),
                    item.get('enchant_name', ''),
                    item.get('quality', 100),
                    item.get('durability', 100),
                    item.get('max_durability', 100),
                    item.get('sealed', 0),
                    item.get('expire_time', 0),
                    extra_data,
                    time.time(),
                ))
            
            return True
        except Exception as e:
            logger.error(f"保存背包失败: {e}")
            return False
    
    def load_inventory(self, character_id: int) -> List[Dict[str, Any]]:
        """
        加载背包数据
        
        Args:
            character_id: 角色ID
            
        Returns:
            背包物品列表
        """
        try:
            results = self.db.query(
                "SELECT * FROM dnf_inventory_items WHERE character_id = ? ORDER BY inventory_type, slot_index",
                (character_id,)
            )
            
            for result in results:
                if result.get('extra_data'):
                    try:
                        result['extra_data'] = json.loads(result['extra_data'])
                    except:
                        result['extra_data'] = {}
            
            return results
        except Exception as e:
            logger.error(f"加载背包失败: {e}")
            return []
    
    # ========== 已装备持久化 ==========
    
    def save_equipped_items(self, character_id: int, equipped_data: Dict[int, Dict[str, Any]]) -> bool:
        """
        保存已装备物品
        
        Args:
            character_id: 角色ID
            equipped_data: 已装备物品字典 {equip_slot: item_data}
            
        Returns:
            是否成功
        """
        try:
            # 先清空旧数据
            self.db.execute(
                "DELETE FROM dnf_equipped_items WHERE character_id = ?",
                (character_id,)
            )
            
            # 插入新数据
            for equip_slot, item in equipped_data.items():
                extra_data = json.dumps(item.get('extra_data', {}), ensure_ascii=False)
                
                self.db.execute("""
                    INSERT INTO dnf_equipped_items (
                        character_id, equip_slot, item_id, item_name,
                        reinforce_level, amplify_level, amplify_type,
                        enchant_card_id, enchant_name, quality, durability, max_durability,
                        sealed, extra_data, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    character_id,
                    equip_slot,
                    item.get('item_id', 0),
                    item.get('item_name', ''),
                    item.get('reinforce_level', 0),
                    item.get('amplify_level', 0),
                    item.get('amplify_type', ''),
                    item.get('enchant_card_id', 0),
                    item.get('enchant_name', ''),
                    item.get('quality', 100),
                    item.get('durability', 100),
                    item.get('max_durability', 100),
                    item.get('sealed', 0),
                    extra_data,
                    time.time(),
                ))
            
            return True
        except Exception as e:
            logger.error(f"保存已装备物品失败: {e}")
            return False
    
    def load_equipped_items(self, character_id: int) -> Dict[int, Dict[str, Any]]:
        """
        加载已装备物品
        
        Args:
            character_id: 角色ID
            
        Returns:
            已装备物品字典 {equip_slot: item_data}
        """
        try:
            results = self.db.query(
                "SELECT * FROM dnf_equipped_items WHERE character_id = ?",
                (character_id,)
            )
            
            equipped = {}
            for result in results:
                if result.get('extra_data'):
                    try:
                        result['extra_data'] = json.loads(result['extra_data'])
                    except:
                        result['extra_data'] = {}
                equipped[result['equip_slot']] = result
            
            return equipped
        except Exception as e:
            logger.error(f"加载已装备物品失败: {e}")
            return {}
    
    # ========== 技能持久化 ==========
    
    def save_skills(self, character_id: int, skills_data: List[Dict[str, Any]]) -> bool:
        """
        保存技能数据
        
        Args:
            character_id: 角色ID
            skills_data: 技能列表
            
        Returns:
            是否成功
        """
        try:
            # 先清空旧数据
            self.db.execute(
                "DELETE FROM dnf_skills WHERE character_id = ?",
                (character_id,)
            )
            
            # 插入新数据
            for skill in skills_data:
                extra_data = json.dumps(skill.get('extra_data', {}), ensure_ascii=False)
                
                self.db.execute("""
                    INSERT INTO dnf_skills (
                        character_id, skill_id, skill_name, level, quick_slot, learn_time, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    character_id,
                    skill.get('skill_id', 0),
                    skill.get('skill_name', ''),
                    skill.get('level', 1),
                    skill.get('quick_slot', -1),
                    skill.get('learn_time', time.time()),
                    extra_data,
                ))
            
            return True
        except Exception as e:
            logger.error(f"保存技能失败: {e}")
            return False
    
    def load_skills(self, character_id: int) -> List[Dict[str, Any]]:
        """
        加载技能数据
        
        Args:
            character_id: 角色ID
            
        Returns:
            技能列表
        """
        try:
            results = self.db.query(
                "SELECT * FROM dnf_skills WHERE character_id = ?",
                (character_id,)
            )
            
            for result in results:
                if result.get('extra_data'):
                    try:
                        result['extra_data'] = json.loads(result['extra_data'])
                    except:
                        result['extra_data'] = {}
            
            return results
        except Exception as e:
            logger.error(f"加载技能失败: {e}")
            return []
    
    def save_skill_points(self, character_id: int, current: int, max_points: int) -> bool:
        """
        保存技能点
        
        Args:
            character_id: 角色ID
            current: 当前技能点
            max_points: 最大技能点
            
        Returns:
            是否成功
        """
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_skill_points WHERE character_id = ?",
                (character_id,)
            )
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_skill_points SET current_points = ?, max_points = ?, updated_at = ?
                    WHERE character_id = ?
                """, (current, max_points, time.time(), character_id))
            else:
                self.db.execute("""
                    INSERT INTO dnf_skill_points (character_id, current_points, max_points, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (character_id, current, max_points, time.time()))
            
            return True
        except Exception as e:
            logger.error(f"保存技能点失败: {e}")
            return False
    
    def load_skill_points(self, character_id: int) -> Tuple[int, int]:
        """
        加载技能点
        
        Args:
            character_id: 角色ID
            
        Returns:
            (当前技能点, 最大技能点)
        """
        try:
            result = self.db.query_one(
                "SELECT * FROM dnf_skill_points WHERE character_id = ?",
                (character_id,)
            )
            if result:
                return result['current_points'], result['max_points']
            return 0, 0
        except Exception as e:
            logger.error(f"加载技能点失败: {e}")
            return 0, 0
    
    # ========== 邮件持久化 ==========
    
    def save_mail(self, mail_data: Dict[str, Any]) -> Optional[int]:
        """
        保存邮件
        
        Args:
            mail_data: 邮件数据
            
        Returns:
            邮件ID
        """
        try:
            # 检查是否已存在
            existing = self.db.query_one(
                "SELECT id FROM dnf_mails WHERE mail_id = ?",
                (mail_data.get('mail_id', 0),)
            )
            
            if existing:
                # 更新
                self.db.execute("""
                    UPDATE dnf_mails SET
                        status = ?, read_time = ?, delete_time = ?,
                        attachment_item_id = ?, attachment_item_name = ?,
                        attachment_count = ?, attachment_gold = ?, attachment_cera = ?
                    WHERE mail_id = ?
                """, (
                    mail_data.get('status', 0),
                    mail_data.get('read_time', 0),
                    mail_data.get('delete_time', 0),
                    mail_data.get('attachment_item_id', 0),
                    mail_data.get('attachment_item_name', ''),
                    mail_data.get('attachment_count', 0),
                    mail_data.get('attachment_gold', 0),
                    mail_data.get('attachment_cera', 0),
                    mail_data.get('mail_id', 0),
                ))
                return existing['id']
            else:
                # 新建
                self.db.execute("""
                    INSERT INTO dnf_mails (
                        mail_id, mail_type, status, sender_id, sender_name,
                        receiver_id, receiver_name, title, content,
                        attachment_item_id, attachment_item_name, attachment_count,
                        attachment_reinforce, attachment_amplify, attachment_amplify_type,
                        attachment_gold, attachment_cera,
                        send_time, read_time, delete_time, expire_time, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    mail_data.get('mail_id', 0),
                    mail_data.get('mail_type', 0),
                    mail_data.get('status', 0),
                    mail_data.get('sender_id', ''),
                    mail_data.get('sender_name', ''),
                    mail_data.get('receiver_id', ''),
                    mail_data.get('receiver_name', ''),
                    mail_data.get('title', ''),
                    mail_data.get('content', ''),
                    mail_data.get('attachment_item_id', 0),
                    mail_data.get('attachment_item_name', ''),
                    mail_data.get('attachment_count', 0),
                    mail_data.get('attachment_reinforce', 0),
                    mail_data.get('attachment_amplify', 0),
                    mail_data.get('attachment_amplify_type', ''),
                    mail_data.get('attachment_gold', 0),
                    mail_data.get('attachment_cera', 0),
                    mail_data.get('send_time', time.time()),
                    mail_data.get('read_time', 0),
                    mail_data.get('delete_time', 0),
                    mail_data.get('expire_time', 0),
                    json.dumps(mail_data.get('extra_data', {}), ensure_ascii=False),
                ))
                
                result = self.db.query_one(
                    "SELECT id FROM dnf_mails WHERE mail_id = ?",
                    (mail_data.get('mail_id', 0),)
                )
                return result['id'] if result else None
                
        except Exception as e:
            logger.error(f"保存邮件失败: {e}")
            return None
    
    def load_mails_by_receiver(self, receiver_id: str, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        加载收件人邮件
        
        Args:
            receiver_id: 收件人ID
            include_deleted: 是否包含已删除邮件
            
        Returns:
            邮件列表
        """
        try:
            if include_deleted:
                results = self.db.query(
                    "SELECT * FROM dnf_mails WHERE receiver_id = ? ORDER BY send_time DESC",
                    (receiver_id,)
                )
            else:
                results = self.db.query(
                    "SELECT * FROM dnf_mails WHERE receiver_id = ? AND status != 2 ORDER BY send_time DESC",
                    (receiver_id,)
                )
            
            for result in results:
                if result.get('extra_data'):
                    try:
                        result['extra_data'] = json.loads(result['extra_data'])
                    except:
                        result['extra_data'] = {}
            
            return results
        except Exception as e:
            logger.error(f"加载邮件失败: {e}")
            return []
    
    def get_next_mail_id(self) -> int:
        """获取下一个邮件ID"""
        try:
            result = self.db.query_one("SELECT MAX(mail_id) as max_id FROM dnf_mails")
            if result and result.get('max_id'):
                return result['max_id'] + 1
            return 1
        except Exception:
            return 1
    
    # ========== 账号持久化 ==========
    
    def save_account(self, account_data: Dict[str, Any]) -> Optional[int]:
        """
        保存账号
        
        Args:
            account_data: 账号数据
            
        Returns:
            账号ID
        """
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_accounts WHERE username = ?",
                (account_data.get('username', ''),)
            )
            
            now = time.time()
            extra_data = json.dumps(account_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_accounts SET
                        password = ?, cera = ?, gold = ?, last_login_at = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    account_data.get('password', ''),
                    account_data.get('cera', 0),
                    account_data.get('gold', 0),
                    now,
                    extra_data,
                    existing['id'],
                ))
                return existing['id']
            else:
                self.db.execute("""
                    INSERT INTO dnf_accounts (username, password, cera, gold, created_at, last_login_at, extra_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_data.get('username', ''),
                    account_data.get('password', ''),
                    account_data.get('cera', 0),
                    account_data.get('gold', 0),
                    now,
                    now,
                    extra_data,
                ))
                
                result = self.db.query_one(
                    "SELECT id FROM dnf_accounts WHERE username = ?",
                    (account_data.get('username', ''),)
                )
                return result['id'] if result else None
                
        except Exception as e:
            logger.error(f"保存账号失败: {e}")
            return None
    
    def load_account(self, username: str) -> Optional[Dict[str, Any]]:
        """
        加载账号
        
        Args:
            username: 用户名
            
        Returns:
            账号数据
        """
        try:
            result = self.db.query_one(
                "SELECT * FROM dnf_accounts WHERE username = ?",
                (username,)
            )
            if result and result.get('extra_data'):
                try:
                    result['extra_data'] = json.loads(result['extra_data'])
                except:
                    result['extra_data'] = {}
            return result
        except Exception as e:
            logger.error(f"加载账号失败: {e}")
            return None
    
    # ========== 副本持久化 ==========
    
    def save_dungeon_record(self, record_data: Dict[str, Any]) -> bool:
        """保存副本通关记录"""
        try:
            now = time.time()
            existing = self.db.query_one(
                "SELECT id FROM dnf_dungeon_records WHERE character_id = ? AND dungeon_id = ? AND difficulty = ?",
                (record_data.get('character_id', ''), record_data.get('dungeon_id', 0), record_data.get('difficulty', 0))
            )
            
            items_reward = json.dumps(record_data.get('items_reward', []), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_dungeon_records SET
                        clear_time = ?, rank = ?, exp_reward = ?, gold_reward = ?,
                        items_reward = ?, clear_count = clear_count + 1, updated_at = ?
                    WHERE id = ?
                """, (
                    record_data.get('clear_time', 0),
                    record_data.get('rank', ''),
                    record_data.get('exp_reward', 0),
                    record_data.get('gold_reward', 0),
                    items_reward,
                    now,
                    existing['id'],
                ))
            else:
                self.db.execute("""
                    INSERT INTO dnf_dungeon_records (
                        character_id, dungeon_id, dungeon_name, difficulty,
                        clear_time, rank, exp_reward, gold_reward, items_reward,
                        clear_count, first_clear, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record_data.get('character_id', ''),
                    record_data.get('dungeon_id', 0),
                    record_data.get('dungeon_name', ''),
                    record_data.get('difficulty', 0),
                    record_data.get('clear_time', 0),
                    record_data.get('rank', ''),
                    record_data.get('exp_reward', 0),
                    record_data.get('gold_reward', 0),
                    items_reward,
                    1,
                    record_data.get('first_clear', 0),
                    now,
                    now,
                ))
            return True
        except Exception as e:
            logger.error(f"保存副本记录失败: {e}")
            return False
    
    def get_dungeon_records(self, character_id: str) -> List[Dict[str, Any]]:
        """获取角色所有副本通关记录"""
        try:
            results = self.db.query(
                "SELECT * FROM dnf_dungeon_records WHERE character_id = ? ORDER BY updated_at DESC",
                (character_id,)
            )
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取副本记录失败: {e}")
            return []
    
    def get_dungeon_record(self, character_id: str, dungeon_id: int, difficulty: int) -> Optional[Dict[str, Any]]:
        """获取单个副本通关记录"""
        try:
            result = self.db.query_one(
                "SELECT * FROM dnf_dungeon_records WHERE character_id = ? AND dungeon_id = ? AND difficulty = ?",
                (character_id, dungeon_id, difficulty)
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"获取副本记录失败: {e}")
            return None
    
    # ========== 拍卖行持久化 ==========
    
    def save_auction_listing(self, listing_data: Dict[str, Any]) -> bool:
        """保存拍卖行上架记录"""
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_auction_listings WHERE listing_id = ?",
                (listing_data.get('listing_id', 0),)
            )
            
            extra_data = json.dumps(listing_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_auction_listings SET
                        status = ?, sold_time = ?, cancel_time = ?,
                        buyer_id = ?, buyer_name = ?, transaction_fee = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    listing_data.get('status', 0),
                    listing_data.get('sold_time', 0),
                    listing_data.get('cancel_time', 0),
                    listing_data.get('buyer_id', ''),
                    listing_data.get('buyer_name', ''),
                    listing_data.get('transaction_fee', 0),
                    extra_data,
                    existing['id'],
                ))
            else:
                self.db.execute("""
                    INSERT INTO dnf_auction_listings (
                        listing_id, seller_id, seller_name, item_id, item_name,
                        item_type, item_level, rarity, quantity,
                        reinforce_level, amplify_level, amplify_type,
                        price, unit_price, status, list_time, expire_time,
                        deposit_fee, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    listing_data.get('listing_id', 0),
                    listing_data.get('seller_id', ''),
                    listing_data.get('seller_name', ''),
                    listing_data.get('item_id', 0),
                    listing_data.get('item_name', ''),
                    listing_data.get('item_type', ''),
                    listing_data.get('item_level', 0),
                    listing_data.get('rarity', 0),
                    listing_data.get('quantity', 1),
                    listing_data.get('reinforce_level', 0),
                    listing_data.get('amplify_level', 0),
                    listing_data.get('amplify_type', ''),
                    listing_data.get('price', 0),
                    listing_data.get('unit_price', 0),
                    listing_data.get('status', 0),
                    listing_data.get('list_time', time.time()),
                    listing_data.get('expire_time', 0),
                    listing_data.get('deposit_fee', 0),
                    extra_data,
                ))
            return True
        except Exception as e:
            logger.error(f"保存拍卖行上架记录失败: {e}")
            return False
    
    def get_auction_listings(self, status: int = 0) -> List[Dict[str, Any]]:
        """获取拍卖行上架列表"""
        try:
            results = self.db.query(
                "SELECT * FROM dnf_auction_listings WHERE status = ? ORDER BY list_time DESC",
                (status,)
            )
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取拍卖行列表失败: {e}")
            return []
    
    def save_auction_transaction(self, transaction_data: Dict[str, Any]) -> bool:
        """保存拍卖行交易记录"""
        try:
            extra_data = json.dumps(transaction_data.get('extra_data', {}), ensure_ascii=False)
            self.db.execute("""
                INSERT OR IGNORE INTO dnf_auction_transactions (
                    transaction_id, listing_id, item_id, item_name, quantity,
                    price, transaction_fee, seller_income,
                    seller_id, seller_name, buyer_id, buyer_name,
                    transaction_time, extra_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction_data.get('transaction_id', 0),
                transaction_data.get('listing_id', 0),
                transaction_data.get('item_id', 0),
                transaction_data.get('item_name', ''),
                transaction_data.get('quantity', 1),
                transaction_data.get('price', 0),
                transaction_data.get('transaction_fee', 0),
                transaction_data.get('seller_income', 0),
                transaction_data.get('seller_id', ''),
                transaction_data.get('seller_name', ''),
                transaction_data.get('buyer_id', ''),
                transaction_data.get('buyer_name', ''),
                transaction_data.get('transaction_time', time.time()),
                extra_data,
            ))
            return True
        except Exception as e:
            logger.error(f"保存拍卖行交易记录失败: {e}")
            return False
    
    # ========== 公会持久化 ==========
    
    def save_guild(self, guild_data: Dict[str, Any]) -> bool:
        """保存公会"""
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_guilds WHERE guild_id = ?",
                (guild_data.get('guild_id', 0),)
            )
            
            extra_data = json.dumps(guild_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_guilds SET
                        guild_notice = ?, guild_introduction = ?, level = ?, exp = ?,
                        exp_to_next_level = ?, funds = ?, member_count = ?,
                        max_members = ?, emblem_id = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    guild_data.get('guild_notice', ''),
                    guild_data.get('guild_introduction', ''),
                    guild_data.get('level', 1),
                    guild_data.get('exp', 0),
                    guild_data.get('exp_to_next_level', 100000),
                    guild_data.get('funds', 0),
                    guild_data.get('member_count', 0),
                    guild_data.get('max_members', 100),
                    guild_data.get('emblem_id', 0),
                    extra_data,
                    existing['id'],
                ))
            else:
                self.db.execute("""
                    INSERT INTO dnf_guilds (
                        guild_id, guild_name, guild_notice, guild_introduction,
                        master_id, master_name, level, max_level, exp,
                        exp_to_next_level, funds, member_count, max_members,
                        emblem_id, create_time, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    guild_data.get('guild_id', 0),
                    guild_data.get('guild_name', ''),
                    guild_data.get('guild_notice', ''),
                    guild_data.get('guild_introduction', ''),
                    guild_data.get('master_id', ''),
                    guild_data.get('master_name', ''),
                    guild_data.get('level', 1),
                    guild_data.get('max_level', 10),
                    guild_data.get('exp', 0),
                    guild_data.get('exp_to_next_level', 100000),
                    guild_data.get('funds', 0),
                    guild_data.get('member_count', 0),
                    guild_data.get('max_members', 100),
                    guild_data.get('emblem_id', 0),
                    guild_data.get('create_time', time.time()),
                    extra_data,
                ))
            return True
        except Exception as e:
            logger.error(f"保存公会失败: {e}")
            return False
    
    def get_guild(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """获取公会"""
        try:
            result = self.db.query_one(
                "SELECT * FROM dnf_guilds WHERE guild_id = ?",
                (guild_id,)
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"获取公会失败: {e}")
            return None
    
    def get_all_guilds(self) -> List[Dict[str, Any]]:
        """获取所有公会"""
        try:
            results = self.db.query("SELECT * FROM dnf_guilds ORDER BY level DESC, member_count DESC")
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取所有公会失败: {e}")
            return []
    
    def delete_guild(self, guild_id: int) -> bool:
        """删除公会"""
        try:
            self.db.execute("DELETE FROM dnf_guilds WHERE guild_id = ?", (guild_id,))
            self.db.execute("DELETE FROM dnf_guild_members WHERE guild_id = ?", (guild_id,))
            self.db.execute("DELETE FROM dnf_guild_applications WHERE guild_id = ?", (guild_id,))
            return True
        except Exception as e:
            logger.error(f"删除公会失败: {e}")
            return False
    
    def save_guild_member(self, member_data: Dict[str, Any]) -> bool:
        """保存公会成员"""
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_guild_members WHERE character_id = ?",
                (member_data.get('character_id', ''),)
            )
            
            extra_data = json.dumps(member_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_guild_members SET
                        guild_id = ?, rank = ?, level = ?, contribution = ?,
                        weekly_contribution = ?, is_online = ?, last_login_time = ?,
                        rank_change_time = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    member_data.get('guild_id', 0),
                    member_data.get('rank', 4),
                    member_data.get('level', 1),
                    member_data.get('contribution', 0),
                    member_data.get('weekly_contribution', 0),
                    member_data.get('is_online', 0),
                    member_data.get('last_login_time', 0),
                    member_data.get('rank_change_time', 0),
                    extra_data,
                    existing['id'],
                ))
            else:
                self.db.execute("""
                    INSERT INTO dnf_guild_members (
                        guild_id, character_id, character_name, account_id,
                        rank, level, job, contribution, weekly_contribution,
                        is_online, last_login_time, join_time, rank_change_time, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    member_data.get('guild_id', 0),
                    member_data.get('character_id', ''),
                    member_data.get('character_name', ''),
                    member_data.get('account_id', ''),
                    member_data.get('rank', 4),
                    member_data.get('level', 1),
                    member_data.get('job', ''),
                    member_data.get('contribution', 0),
                    member_data.get('weekly_contribution', 0),
                    member_data.get('is_online', 0),
                    member_data.get('last_login_time', 0),
                    member_data.get('join_time', time.time()),
                    member_data.get('rank_change_time', 0),
                    extra_data,
                ))
            return True
        except Exception as e:
            logger.error(f"保存公会成员失败: {e}")
            return False
    
    def get_guild_members(self, guild_id: int) -> List[Dict[str, Any]]:
        """获取公会成员列表"""
        try:
            results = self.db.query(
                "SELECT * FROM dnf_guild_members WHERE guild_id = ? ORDER BY rank ASC, contribution DESC",
                (guild_id,)
            )
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取公会成员失败: {e}")
            return []
    
    def delete_guild_member(self, character_id: str) -> bool:
        """删除公会成员"""
        try:
            self.db.execute("DELETE FROM dnf_guild_members WHERE character_id = ?", (character_id,))
            return True
        except Exception as e:
            logger.error(f"删除公会成员失败: {e}")
            return False
    
    def save_guild_application(self, application_data: Dict[str, Any]) -> bool:
        """保存公会申请"""
        try:
            existing = self.db.query_one(
                "SELECT id FROM dnf_guild_applications WHERE application_id = ?",
                (application_data.get('application_id', 0),)
            )
            
            extra_data = json.dumps(application_data.get('extra_data', {}), ensure_ascii=False)
            
            if existing:
                self.db.execute("""
                    UPDATE dnf_guild_applications SET
                        status = ?, process_time = ?, processed_by = ?, extra_data = ?
                    WHERE id = ?
                """, (
                    application_data.get('status', 0),
                    application_data.get('process_time', 0),
                    application_data.get('processed_by', ''),
                    extra_data,
                    existing['id'],
                ))
            else:
                self.db.execute("""
                    INSERT INTO dnf_guild_applications (
                        application_id, guild_id, character_id, character_name,
                        account_id, status, message, level, job,
                        apply_time, process_time, processed_by, extra_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    application_data.get('application_id', 0),
                    application_data.get('guild_id', 0),
                    application_data.get('character_id', ''),
                    application_data.get('character_name', ''),
                    application_data.get('account_id', ''),
                    application_data.get('status', 0),
                    application_data.get('message', ''),
                    application_data.get('level', 1),
                    application_data.get('job', ''),
                    application_data.get('apply_time', time.time()),
                    application_data.get('process_time', 0),
                    application_data.get('processed_by', ''),
                    extra_data,
                ))
            return True
        except Exception as e:
            logger.error(f"保存公会申请失败: {e}")
            return False
    
    def get_guild_applications(self, guild_id: int, status: int = 0) -> List[Dict[str, Any]]:
        """获取公会申请列表"""
        try:
            results = self.db.query(
                "SELECT * FROM dnf_guild_applications WHERE guild_id = ? AND status = ? ORDER BY apply_time DESC",
                (guild_id, status)
            )
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"获取公会申请失败: {e}")
            return []
    
    # ========== 统计信息 ==========
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            stats = {}
            
            # 账号数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_accounts")
            stats['accounts'] = result['count'] if result else 0
            
            # 角色数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_characters")
            stats['characters'] = result['count'] if result else 0
            
            # 邮件数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_mails")
            stats['mails'] = result['count'] if result else 0
            
            # 背包物品数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_inventory_items")
            stats['inventory_items'] = result['count'] if result else 0
            
            # 副本记录数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_dungeon_records")
            stats['dungeon_records'] = result['count'] if result else 0
            
            # 拍卖行上架数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_auction_listings")
            stats['auction_listings'] = result['count'] if result else 0
            
            # 拍卖行交易数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_auction_transactions")
            stats['auction_transactions'] = result['count'] if result else 0
            
            # 公会数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_guilds")
            stats['guilds'] = result['count'] if result else 0
            
            # 公会成员数
            result = self.db.query_one("SELECT COUNT(*) as count FROM dnf_guild_members")
            stats['guild_members'] = result['count'] if result else 0
            
            return stats
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}


# 全局数据持久化实例
_persistence: Optional[DataPersistence] = None


def get_persistence() -> DataPersistence:
    """获取全局数据持久化实例"""
    global _persistence
    if _persistence is None:
        _persistence = DataPersistence()
    return _persistence


def init_persistence() -> bool:
    """初始化全局数据持久化"""
    global _persistence
    _persistence = DataPersistence()
    return _persistence.initialize()
