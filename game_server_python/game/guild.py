"""
公会系统模块
实现DNF公会数据模型、创建、加入、退出、成员管理、公会技能等
"""

import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 公会成员职位
class GuildRank(Enum):
    """公会成员职位"""
    MASTER = 0        # 会长
    VICE_MASTER = 1   # 副会长
    OFFICER = 2       # 官员
    MEMBER = 3        # 成员
    NEWBIE = 4        # 新人


# 公会申请状态
class GuildApplicationStatus(Enum):
    """公会申请状态"""
    PENDING = 0       # 待处理
    APPROVED = 1      # 已批准
    REJECTED = 2      # 已拒绝
    CANCELLED = 3     # 已取消


# 公会技能类型
class GuildSkillType(Enum):
    """公会技能类型"""
    PASSIVE = "passive"      # 被动技能
    ACTIVE = "active"        # 主动技能
    BUFF = "buff"            # BUFF技能


@dataclass
class GuildMember:
    """公会成员"""
    character_id: str = ""
    character_name: str = ""
    account_id: str = ""
    
    # 职位
    rank: int = GuildRank.NEWBIE.value
    
    # 等级和职业
    level: int = 1
    job: str = ""
    
    # 贡献度
    contribution: int = 0
    weekly_contribution: int = 0
    
    # 在线状态
    is_online: bool = False
    last_login_time: float = 0.0
    
    # 加入时间
    join_time: float = 0.0
    
    # 职位变更时间
    rank_change_time: float = 0.0
    
    def __post_init__(self):
        if not self.join_time:
            self.join_time = time.time()
        if not self.last_login_time:
            self.last_login_time = time.time()
    
    @property
    def rank_name(self) -> str:
        """职位名称"""
        rank_names = {
            GuildRank.MASTER.value: "会长",
            GuildRank.VICE_MASTER.value: "副会长",
            GuildRank.OFFICER.value: "官员",
            GuildRank.MEMBER.value: "成员",
            GuildRank.NEWBIE.value: "新人",
        }
        return rank_names.get(self.rank, "未知")
    
    def to_dict(self) -> dict:
        """转换为字典"""
        data = asdict(self)
        data['rank_name'] = self.rank_name
        return data


@dataclass
class GuildSkill:
    """公会技能"""
    skill_id: int = 0
    skill_name: str = ""
    skill_type: str = GuildSkillType.PASSIVE.value
    description: str = ""
    
    # 等级
    max_level: int = 10
    current_level: int = 0
    
    # 升级消耗
    cost_per_level: int = 100000  # 每级消耗的公会资金
    
    # 效果
    effect: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class GuildApplication:
    """公会申请"""
    application_id: int = 0
    guild_id: int = 0
    character_id: str = ""
    character_name: str = ""
    account_id: str = ""
    
    # 状态
    status: int = GuildApplicationStatus.PENDING.value
    
    # 申请信息
    message: str = ""
    level: int = 1
    job: str = ""
    
    # 时间
    apply_time: float = 0.0
    process_time: float = 0.0
    
    # 处理人
    processed_by: str = ""
    
    def __post_init__(self):
        if not self.apply_time:
            self.apply_time = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class Guild:
    """公会"""
    guild_id: int = 0
    guild_name: str = ""
    guild_notice: str = ""
    guild_introduction: str = ""
    
    # 会长
    master_id: str = ""
    master_name: str = ""
    
    # 等级
    level: int = 1
    max_level: int = 10
    
    # 经验值
    exp: int = 0
    exp_to_next_level: int = 100000
    
    # 资金
    funds: int = 0
    
    # 成员
    members: Dict[str, GuildMember] = field(default_factory=dict)
    max_members: int = 100
    
    # 技能
    skills: Dict[int, GuildSkill] = field(default_factory=dict)
    
    # 申请列表
    applications: Dict[int, GuildApplication] = field(default_factory=dict)
    
    # 时间
    create_time: float = 0.0
    
    # 公会徽章
    emblem_id: int = 0
    
    # 额外数据
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.create_time:
            self.create_time = time.time()
    
    @property
    def member_count(self) -> int:
        """成员数量"""
        return len(self.members)
    
    @property
    def online_member_count(self) -> int:
        """在线成员数量"""
        return sum(1 for m in self.members.values() if m.is_online)
    
    @property
    def total_contribution(self) -> int:
        """总贡献度"""
        return sum(m.contribution for m in self.members.values())
    
    def add_member(self, member: GuildMember) -> bool:
        """添加成员"""
        if self.member_count >= self.max_members:
            return False
        if member.character_id in self.members:
            return False
        self.members[member.character_id] = member
        return True
    
    def remove_member(self, character_id: str) -> bool:
        """移除成员"""
        if character_id not in self.members:
            return False
        if character_id == self.master_id:
            return False  # 不能移除会长
        del self.members[character_id]
        return True
    
    def get_member(self, character_id: str) -> Optional[GuildMember]:
        """获取成员"""
        return self.members.get(character_id)
    
    def change_member_rank(self, character_id: str, new_rank: int) -> bool:
        """变更成员职位"""
        member = self.get_member(character_id)
        if not member:
            return False
        if member.rank == GuildRank.MASTER.value:
            return False  # 不能变更会长职位
        member.rank = new_rank
        member.rank_change_time = time.time()
        return True
    
    def add_application(self, application: GuildApplication) -> bool:
        """添加申请"""
        self.applications[application.application_id] = application
        return True
    
    def process_application(
        self,
        application_id: int,
        approved: bool,
        processed_by: str = "",
    ) -> Tuple[bool, str]:
        """处理申请"""
        application = self.applications.get(application_id)
        if not application:
            return False, "申请不存在"
        
        if application.status != GuildApplicationStatus.PENDING.value:
            return False, "申请已处理"
        
        if approved:
            # 检查成员数量
            if self.member_count >= self.max_members:
                return False, "公会成员已满"
            
            # 添加成员
            member = GuildMember(
                character_id=application.character_id,
                character_name=application.character_name,
                account_id=application.account_id,
                rank=GuildRank.NEWBIE.value,
                level=application.level,
                job=application.job,
            )
            if not self.add_member(member):
                return False, "添加成员失败"
            
            application.status = GuildApplicationStatus.APPROVED.value
        else:
            application.status = GuildApplicationStatus.REJECTED.value
        
        application.process_time = time.time()
        application.processed_by = processed_by
        
        return True, ""
    
    def add_funds(self, amount: int) -> bool:
        """增加公会资金"""
        if amount <= 0:
            return False
        self.funds += amount
        return True
    
    def spend_funds(self, amount: int) -> bool:
        """消耗公会资金"""
        if amount <= 0 or self.funds < amount:
            return False
        self.funds -= amount
        return True
    
    def add_exp(self, amount: int) -> bool:
        """增加公会经验"""
        if amount <= 0:
            return False
        self.exp += amount
        
        # 检查升级
        while self.exp >= self.exp_to_next_level and self.level < self.max_level:
            self.exp -= self.exp_to_next_level
            self.level += 1
            self.exp_to_next_level = int(self.exp_to_next_level * 1.5)
            self.max_members = min(self.max_members + 10, 300)
            logger.info(f"公会{self.guild_name}升级到{self.level}级")
        
        return True
    
    def upgrade_skill(self, skill_id: int) -> Tuple[bool, str]:
        """升级公会技能"""
        skill = self.skills.get(skill_id)
        if not skill:
            return False, "技能不存在"
        
        if skill.current_level >= skill.max_level:
            return False, "技能已满级"
        
        cost = skill.cost_per_level * (skill.current_level + 1)
        if not self.spend_funds(cost):
            return False, f"公会资金不足，需要{cost}金币"
        
        skill.current_level += 1
        return True, ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "guild_id": self.guild_id,
            "guild_name": self.guild_name,
            "guild_notice": self.guild_notice,
            "guild_introduction": self.guild_introduction,
            "master_id": self.master_id,
            "master_name": self.master_name,
            "level": self.level,
            "max_level": self.max_level,
            "exp": self.exp,
            "exp_to_next_level": self.exp_to_next_level,
            "funds": self.funds,
            "member_count": self.member_count,
            "max_members": self.max_members,
            "online_member_count": self.online_member_count,
            "total_contribution": self.total_contribution,
            "members": [m.to_dict() for m in self.members.values()],
            "skills": [s.to_dict() for s in self.skills.values()],
            "pending_applications": len([a for a in self.applications.values() if a.status == GuildApplicationStatus.PENDING.value]),
            "create_time": self.create_time,
            "emblem_id": self.emblem_id,
        }


class GuildManager:
    """公会管理器"""
    
    def __init__(self):
        # 公会列表（guild_id -> Guild）
        self._guilds: Dict[int, Guild] = {}
        
        # 公会名称索引（guild_name -> guild_id）
        self._guild_name_index: Dict[str, int] = {}
        
        # 角色公会索引（character_id -> guild_id）
        self._character_guild_index: Dict[str, int] = {}
        
        # ID计数器
        self._guild_id_counter = 0
        self._application_id_counter = 0
        
        # 创建公会消耗
        self.create_guild_cost = 1000000  # 100万金币
    
    def create_guild(
        self,
        guild_name: str,
        master_id: str,
        master_name: str,
        master_account_id: str = "",
        master_level: int = 1,
        master_job: str = "",
        guild_notice: str = "",
        guild_introduction: str = "",
    ) -> Tuple[bool, str, Optional[Guild]]:
        """
        创建公会
        
        Returns:
            (是否成功, 原因, 公会对象)
        """
        # 验证公会名称
        if not guild_name or len(guild_name) < 2 or len(guild_name) > 12:
            return False, "公会名称长度必须在2-12个字符之间", None
        
        # 检查公会名称是否已存在
        if guild_name in self._guild_name_index:
            return False, "公会名称已存在", None
        
        # 检查角色是否已有公会
        if master_id in self._character_guild_index:
            return False, "该角色已加入公会", None
        
        # 创建公会
        self._guild_id_counter += 1
        guild = Guild(
            guild_id=self._guild_id_counter,
            guild_name=guild_name,
            guild_notice=guild_notice,
            guild_introduction=guild_introduction,
            master_id=master_id,
            master_name=master_name,
        )
        
        # 添加会长
        master_member = GuildMember(
            character_id=master_id,
            character_name=master_name,
            account_id=master_account_id,
            rank=GuildRank.MASTER.value,
            level=master_level,
            job=master_job,
        )
        guild.add_member(master_member)
        
        # 保存索引
        self._guilds[guild.guild_id] = guild
        self._guild_name_index[guild_name] = guild.guild_id
        self._character_guild_index[master_id] = guild.guild_id
        
        logger.info(f"创建公会: {guild_name}, 会长: {master_name}")
        
        return True, "", guild
    
    def disband_guild(self, guild_id: int, character_id: str) -> Tuple[bool, str]:
        """
        解散公会
        
        Returns:
            (是否成功, 原因)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在"
        
        if guild.master_id != character_id:
            return False, "只有会长才能解散公会"
        
        # 移除所有角色的公会索引
        for member_id in guild.members.keys():
            self._character_guild_index.pop(member_id, None)
        
        # 移除公会名称索引
        self._guild_name_index.pop(guild.guild_name, None)
        
        # 删除公会
        del self._guilds[guild_id]
        
        logger.info(f"解散公会: {guild.guild_name}")
        
        return True, ""
    
    def get_guild(self, guild_id: int) -> Optional[Guild]:
        """获取公会"""
        return self._guilds.get(guild_id)
    
    def get_guild_by_name(self, guild_name: str) -> Optional[Guild]:
        """根据名称获取公会"""
        guild_id = self._guild_name_index.get(guild_name)
        if guild_id:
            return self._guilds.get(guild_id)
        return None
    
    def get_character_guild(self, character_id: str) -> Optional[Guild]:
        """获取角色所在公会"""
        guild_id = self._character_guild_index.get(character_id)
        if guild_id:
            return self._guilds.get(guild_id)
        return None
    
    def get_all_guilds(self) -> List[Guild]:
        """获取所有公会"""
        return list(self._guilds.values())
    
    def search_guilds(
        self,
        keyword: str = "",
        min_level: int = 0,
        max_level: int = 100,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Guild], int]:
        """
        搜索公会
        
        Returns:
            (公会列表, 总数)
        """
        guilds = self.get_all_guilds()
        
        # 关键词过滤
        if keyword:
            keyword_lower = keyword.lower()
            guilds = [
                g for g in guilds
                if keyword_lower in g.guild_name.lower()
            ]
        
        # 等级过滤
        guilds = [g for g in guilds if min_level <= g.level <= max_level]
        
        # 按等级排序
        guilds.sort(key=lambda g: -g.level)
        
        # 分页
        total = len(guilds)
        start = (page - 1) * page_size
        end = start + page_size
        guilds = guilds[start:end]
        
        return guilds, total
    
    def apply_to_guild(
        self,
        guild_id: int,
        character_id: str,
        character_name: str,
        account_id: str = "",
        level: int = 1,
        job: str = "",
        message: str = "",
    ) -> Tuple[bool, str, Optional[GuildApplication]]:
        """
        申请加入公会
        
        Returns:
            (是否成功, 原因, 申请记录)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在", None
        
        # 检查是否已有公会
        if character_id in self._character_guild_index:
            return False, "该角色已加入公会", None
        
        # 检查是否已有待处理的申请
        for app in guild.applications.values():
            if app.character_id == character_id and app.status == GuildApplicationStatus.PENDING.value:
                return False, "已有待处理的申请", None
        
        # 创建申请
        self._application_id_counter += 1
        application = GuildApplication(
            application_id=self._application_id_counter,
            guild_id=guild_id,
            character_id=character_id,
            character_name=character_name,
            account_id=account_id,
            message=message,
            level=level,
            job=job,
        )
        
        guild.add_application(application)
        
        logger.info(f"角色{character_name}申请加入公会{guild.guild_name}")
        
        return True, "", application
    
    def process_application(
        self,
        guild_id: int,
        application_id: int,
        approved: bool,
        processed_by: str = "",
    ) -> Tuple[bool, str]:
        """
        处理公会申请
        
        Returns:
            (是否成功, 原因)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在"
        
        success, reason = guild.process_application(application_id, approved, processed_by)
        
        if success and approved:
            application = guild.applications.get(application_id)
            if application:
                self._character_guild_index[application.character_id] = guild_id
                logger.info(f"角色{application.character_name}加入公会{guild.guild_name}")
        
        return success, reason
    
    def leave_guild(self, character_id: str) -> Tuple[bool, str]:
        """
        退出公会
        
        Returns:
            (是否成功, 原因)
        """
        guild = self.get_character_guild(character_id)
        if not guild:
            return False, "该角色未加入公会"
        
        if guild.master_id == character_id:
            return False, "会长不能退出公会，请先转让会长职位"
        
        # 移除成员
        guild.remove_member(character_id)
        
        # 移除索引
        self._character_guild_index.pop(character_id, None)
        
        logger.info(f"角色退出公会: {guild.guild_name}")
        
        return True, ""
    
    def kick_member(
        self,
        guild_id: int,
        character_id: str,
        kicked_by: str = "",
    ) -> Tuple[bool, str]:
        """
        踢出成员
        
        Returns:
            (是否成功, 原因)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在"
        
        member = guild.get_member(character_id)
        if not member:
            return False, "成员不存在"
        
        if member.rank == GuildRank.MASTER.value:
            return False, "不能踢出会长"
        
        # 移除成员
        guild.remove_member(character_id)
        
        # 移除索引
        self._character_guild_index.pop(character_id, None)
        
        logger.info(f"角色被踢出公会: {guild.guild_name}")
        
        return True, ""
    
    def change_member_rank(
        self,
        guild_id: int,
        character_id: str,
        new_rank: int,
        changed_by: str = "",
    ) -> Tuple[bool, str]:
        """
        变更成员职位
        
        Returns:
            (是否成功, 原因)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在"
        
        success = guild.change_member_rank(character_id, new_rank)
        if not success:
            return False, "变更职位失败"
        
        logger.info(f"变更成员职位: {character_id} -> {new_rank}")
        
        return True, ""
    
    def transfer_master(
        self,
        guild_id: int,
        new_master_id: str,
        old_master_id: str,
    ) -> Tuple[bool, str]:
        """
        转让会长
        
        Returns:
            (是否成功, 原因)
        """
        guild = self._guilds.get(guild_id)
        if not guild:
            return False, "公会不存在"
        
        if guild.master_id != old_master_id:
            return False, "只有会长才能转让"
        
        new_master = guild.get_member(new_master_id)
        if not new_master:
            return False, "新会长不在公会中"
        
        # 变更职位
        old_master = guild.get_member(old_master_id)
        if old_master:
            old_master.rank = GuildRank.MEMBER.value
            old_master.rank_change_time = time.time()
        
        new_master.rank = GuildRank.MASTER.value
        new_master.rank_change_time = time.time()
        
        # 更新会长信息
        guild.master_id = new_master_id
        guild.master_name = new_master.character_name
        
        logger.info(f"公会{guild.guild_name}转让会长: {old_master_id} -> {new_master_id}")
        
        return True, ""
    
    def add_contribution(
        self,
        character_id: str,
        amount: int,
    ) -> Tuple[bool, str]:
        """
        增加贡献度
        
        Returns:
            (是否成功, 原因)
        """
        guild = self.get_character_guild(character_id)
        if not guild:
            return False, "该角色未加入公会"
        
        member = guild.get_member(character_id)
        if not member:
            return False, "成员不存在"
        
        member.contribution += amount
        member.weekly_contribution += amount
        
        # 增加公会经验
        guild.add_exp(amount // 10)
        
        return True, ""
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        guilds = self.get_all_guilds()
        
        total_members = sum(g.member_count for g in guilds)
        total_funds = sum(g.funds for g in guilds)
        
        # 按等级统计
        level_stats = {}
        for guild in guilds:
            level = guild.level
            if level not in level_stats:
                level_stats[level] = 0
            level_stats[level] += 1
        
        return {
            "total_guilds": len(guilds),
            "total_members": total_members,
            "total_funds": total_funds,
            "level_stats": level_stats,
        }
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "guilds_count": len(self._guilds),
            "statistics": self.get_statistics(),
            "guilds": [g.to_dict() for g in self.get_all_guilds()],
        }
