"""
技能系统模块
实现DNF技能数据模型、技能学习、技能升级、技能快捷键等
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 技能类型
class SkillType(Enum):
    """技能类型"""
    ACTIVE = "active"            # 主动技能
    PASSIVE = "passive"          # 被动技能
    BUFF = "buff"                # BUFF技能
    DANCE = "dance"              # 舞蹈技能
    AWAKENING = "awakening"      # 觉醒技能
    HYPER = "hyper"              # 二觉技能
    OTHER = "other"              # 其他


# 技能快捷键槽位
class SkillQuickSlot(Enum):
    """技能快捷键槽位"""
    SLOT_A = 0
    SLOT_S = 1
    SLOT_D = 2
    SLOT_F = 3
    SLOT_G = 4
    SLOT_H = 5
    SLOT_Q = 6
    SLOT_W = 7
    SLOT_E = 8
    SLOT_R = 9
    SLOT_T = 10
    SLOT_Y = 11


@dataclass
class SkillTemplate:
    """技能模板"""
    skill_id: int = 0
    skill_name: str = ""
    skill_type: str = SkillType.ACTIVE.value
    description: str = ""
    
    # 职业限制
    job_required: List[str] = field(default_factory=list)
    level_required: int = 0
    grow_type_required: int = -1  # -1表示不限制
    
    # 技能等级
    max_level: int = 1
    base_level: int = 0
    
    # 消耗
    mp_cost: int = 0
    cooldown: float = 0.0
    hp_cost: int = 0
    cube_cost: int = 0  # 无色小晶块消耗
    
    # 属性成长（每级）
    damage_per_level: int = 0
    mp_cost_per_level: int = 0
    cooldown_per_level: float = 0.0
    
    # 前置技能
    prerequisite_skills: Dict[int, int] = field(default_factory=dict)  # skill_id -> required_level
    
    # 图标
    icon_path: str = ""
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "SkillTemplate":
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class LearnedSkill:
    """已学习技能"""
    skill_id: int = 0
    skill_name: str = ""
    level: int = 1
    learn_time: float = 0.0
    
    # 快捷键槽位（-1表示未设置）
    quick_slot: int = -1
    
    # 冷却结束时间
    cooldown_end_time: float = 0.0
    
    def __post_init__(self):
        if not self.learn_time:
            self.learn_time = time.time()
    
    @property
    def is_on_cooldown(self) -> bool:
        """是否在冷却中"""
        return time.time() < self.cooldown_end_time
    
    @property
    def cooldown_remaining(self) -> float:
        """剩余冷却时间"""
        remaining = self.cooldown_end_time - time.time()
        return max(0, remaining)
    
    def start_cooldown(self, cooldown: float) -> None:
        """开始冷却"""
        self.cooldown_end_time = time.time() + cooldown
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class SkillBuild:
    """技能加点方案"""
    build_id: int = 0
    build_name: str = ""
    skills: Dict[int, int] = field(default_factory=dict)  # skill_id -> level
    quick_slots: Dict[int, int] = field(default_factory=dict)  # slot -> skill_id
    create_time: float = 0.0
    update_time: float = 0.0
    
    def __post_init__(self):
        now = time.time()
        if not self.create_time:
            self.create_time = now
        if not self.update_time:
            self.update_time = now
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class SkillManager:
    """技能管理器"""
    
    def __init__(self):
        # 技能模板（skill_id -> SkillTemplate）
        self._skill_templates: Dict[int, SkillTemplate] = {}
        
        # 角色已学习技能（character_id -> {skill_id -> LearnedSkill}）
        self._learned_skills: Dict[str, Dict[int, LearnedSkill]] = {}
        
        # 角色技能点（character_id -> (current, max)）
        self._skill_points: Dict[str, Tuple[int, int]] = {}
        
        # 角色加点方案（character_id -> [SkillBuild]）
        self._skill_builds: Dict[str, List[SkillBuild]] = {}
    
    def register_skill_template(self, skill: SkillTemplate) -> None:
        """注册技能模板"""
        self._skill_templates[skill.skill_id] = skill
    
    def get_skill_template(self, skill_id: int) -> Optional[SkillTemplate]:
        """获取技能模板"""
        return self._skill_templates.get(skill_id)
    
    def get_learned_skills(self, character_id: str) -> Dict[int, LearnedSkill]:
        """获取角色已学习技能"""
        if character_id not in self._learned_skills:
            self._learned_skills[character_id] = {}
        return self._learned_skills[character_id]
    
    def get_skill_points(self, character_id: str) -> Tuple[int, int]:
        """获取技能点"""
        if character_id not in self._skill_points:
            self._skill_points[character_id] = (0, 0)
        return self._skill_points[character_id]
    
    def set_skill_points(self, character_id: str, current: int, max_points: int) -> None:
        """设置技能点"""
        self._skill_points[character_id] = (current, max_points)
    
    def add_skill_points(self, character_id: str, points: int) -> None:
        """增加技能点"""
        current, max_points = self.get_skill_points(character_id)
        self._skill_points[character_id] = (current + points, max_points + points)
    
    def can_learn_skill(
        self,
        character_id: str,
        skill_id: int,
        character_job: str = "",
        character_level: int = 1,
    ) -> Tuple[bool, str]:
        """
        检查是否可以学习技能
        
        Returns:
            (是否可以, 原因)
        """
        template = self.get_skill_template(skill_id)
        if not template:
            return False, "技能不存在"
        
        # 检查职业限制
        if template.job_required and character_job not in template.job_required:
            return False, "职业不符合"
        
        # 检查等级限制
        if character_level < template.level_required:
            return False, f"等级不足（需要{template.level_required}级）"
        
        # 检查前置技能
        learned = self.get_learned_skills(character_id)
        for pre_skill_id, pre_level in template.prerequisite_skills.items():
            if pre_skill_id not in learned:
                pre_template = self.get_skill_template(pre_skill_id)
                pre_name = pre_template.skill_name if pre_template else f"技能{pre_skill_id}"
                return False, f"需要前置技能：{pre_name} Lv.{pre_level}"
            if learned[pre_skill_id].level < pre_level:
                pre_template = self.get_skill_template(pre_skill_id)
                pre_name = pre_template.skill_name if pre_template else f"技能{pre_skill_id}"
                return False, f"前置技能等级不足：{pre_name}需要Lv.{pre_level}"
        
        # 检查是否已达最高等级
        if skill_id in learned:
            if learned[skill_id].level >= template.max_level:
                return False, "已达最高等级"
        
        # 检查技能点
        current, _ = self.get_skill_points(character_id)
        if current <= 0:
            return False, "技能点不足"
        
        return True, ""
    
    def learn_skill(
        self,
        character_id: str,
        skill_id: int,
        character_job: str = "",
        character_level: int = 1,
    ) -> Tuple[bool, str]:
        """
        学习/升级技能
        
        Returns:
            (是否成功, 原因)
        """
        # 检查是否可以学习
        can_learn, reason = self.can_learn_skill(
            character_id, skill_id, character_job, character_level
        )
        if not can_learn:
            return False, reason
        
        template = self.get_skill_template(skill_id)
        learned = self.get_learned_skills(character_id)
        
        # 消耗技能点
        current, max_points = self.get_skill_points(character_id)
        self._skill_points[character_id] = (current - 1, max_points)
        
        if skill_id in learned:
            # 升级技能
            learned[skill_id].level += 1
            logger.info(f"角色{character_id}升级技能{template.skill_name}到Lv.{learned[skill_id].level}")
        else:
            # 学习新技能
            learned[skill_id] = LearnedSkill(
                skill_id=skill_id,
                skill_name=template.skill_name,
                level=template.base_level + 1,
            )
            logger.info(f"角色{character_id}学习技能{template.skill_name}")
        
        return True, ""
    
    def unlearn_skill(self, character_id: str, skill_id: int) -> Tuple[bool, str]:
        """
        遗忘技能（返还技能点）
        
        Returns:
            (是否成功, 原因)
        """
        learned = self.get_learned_skills(character_id)
        if skill_id not in learned:
            return False, "未学习该技能"
        
        skill = learned[skill_id]
        template = self.get_skill_template(skill_id)
        
        # 返还技能点
        points_to_return = skill.level - template.base_level if template else skill.level
        current, max_points = self.get_skill_points(character_id)
        self._skill_points[character_id] = (current + points_to_return, max_points)
        
        # 移除快捷键
        if skill.quick_slot >= 0:
            self.unset_quick_slot(character_id, skill.quick_slot)
        
        del learned[skill_id]
        logger.info(f"角色{character_id}遗忘技能{skill.skill_name}，返还{points_to_return}技能点")
        
        return True, ""
    
    def set_quick_slot(self, character_id: str, slot: int, skill_id: int) -> bool:
        """设置技能快捷键"""
        learned = self.get_learned_skills(character_id)
        if skill_id not in learned:
            return False
        
        # 如果该槽位已有技能，先移除
        for skill in learned.values():
            if skill.quick_slot == slot:
                skill.quick_slot = -1
                break
        
        learned[skill_id].quick_slot = slot
        return True
    
    def unset_quick_slot(self, character_id: str, slot: int) -> bool:
        """移除技能快捷键"""
        learned = self.get_learned_skills(character_id)
        for skill in learned.values():
            if skill.quick_slot == slot:
                skill.quick_slot = -1
                return True
        return False
    
    def get_quick_slots(self, character_id: str) -> Dict[int, int]:
        """获取技能快捷键映射（slot -> skill_id）"""
        learned = self.get_learned_skills(character_id)
        return {
            skill.quick_slot: skill.skill_id
            for skill in learned.values()
            if skill.quick_slot >= 0
        }
    
    def use_skill(self, character_id: str, skill_id: int) -> Tuple[bool, str]:
        """
        使用技能
        
        Returns:
            (是否成功, 原因)
        """
        learned = self.get_learned_skills(character_id)
        if skill_id not in learned:
            return False, "未学习该技能"
        
        skill = learned[skill_id]
        template = self.get_skill_template(skill_id)
        
        if not template:
            return False, "技能模板不存在"
        
        # 检查冷却
        if skill.is_on_cooldown:
            return False, f"技能冷却中（剩余{skill.cooldown_remaining:.1f}秒）"
        
        # 开始冷却
        if template.cooldown > 0:
            skill.start_cooldown(template.cooldown)
        
        logger.info(f"角色{character_id}使用技能{skill.skill_name}")
        
        return True, ""
    
    def save_skill_build(self, character_id: str, build_name: str) -> Optional[SkillBuild]:
        """保存技能加点方案"""
        learned = self.get_learned_skills(character_id)
        quick_slots = self.get_quick_slots(character_id)
        
        build = SkillBuild(
            build_id=int(time.time()),
            build_name=build_name,
            skills={skill_id: skill.level for skill_id, skill in learned.items()},
            quick_slots=quick_slots,
        )
        
        if character_id not in self._skill_builds:
            self._skill_builds[character_id] = []
        self._skill_builds[character_id].append(build)
        
        logger.info(f"角色{character_id}保存技能方案：{build_name}")
        
        return build
    
    def load_skill_build(self, character_id: str, build_id: int) -> Tuple[bool, str]:
        """加载技能加点方案"""
        if character_id not in self._skill_builds:
            return False, "没有保存的方案"
        
        build = None
        for b in self._skill_builds[character_id]:
            if b.build_id == build_id:
                build = b
                break
        
        if not build:
            return False, "方案不存在"
        
        # 清空当前技能
        learned = self.get_learned_skills(character_id)
        learned.clear()
        
        # 加载方案技能
        for skill_id, level in build.skills.items():
            template = self.get_skill_template(skill_id)
            if template:
                learned[skill_id] = LearnedSkill(
                    skill_id=skill_id,
                    skill_name=template.skill_name,
                    level=level,
                )
        
        # 加载快捷键
        for slot, skill_id in build.quick_slots.items():
            if skill_id in learned:
                learned[skill_id].quick_slot = slot
        
        logger.info(f"角色{character_id}加载技能方案：{build.build_name}")
        
        return True, ""
    
    def get_skill_builds(self, character_id: str) -> List[SkillBuild]:
        """获取角色的技能方案列表"""
        return self._skill_builds.get(character_id, [])
    
    def to_dict(self, character_id: str) -> dict:
        """转换为字典"""
        learned = self.get_learned_skills(character_id)
        current, max_points = self.get_skill_points(character_id)
        
        return {
            "character_id": character_id,
            "skill_points": {"current": current, "max": max_points},
            "learned_skills": {
                str(skill_id): skill.to_dict()
                for skill_id, skill in learned.items()
            },
            "quick_slots": self.get_quick_slots(character_id),
            "skill_builds": [
                build.to_dict()
                for build in self.get_skill_builds(character_id)
            ],
        }
