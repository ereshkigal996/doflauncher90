"""
邮件系统模块
实现DNF邮件发送、接收、附件、删除等功能
"""

import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 邮件类型
class MailType(Enum):
    """邮件类型"""
    NORMAL = 0           # 普通邮件
    SYSTEM = 1           # 系统邮件
    AUCTION = 2          # 拍卖行邮件
    GUILD = 3            # 公会邮件
    FRIEND = 4           # 好友邮件
    OTHER = 5            # 其他


# 邮件状态
class MailStatus(Enum):
    """邮件状态"""
    UNREAD = 0           # 未读
    READ = 1             # 已读
    DELETED = 2          # 已删除


@dataclass
class MailAttachment:
    """邮件附件"""
    item_id: int = 0
    item_name: str = ""
    count: int = 1
    reinforce_level: int = 0
    amplify_level: int = 0
    amplify_type: str = ""
    
    # 金币
    gold: int = 0
    
    # 点券
    cera: int = 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class Mail:
    """邮件"""
    mail_id: int = 0
    mail_type: int = MailType.NORMAL.value
    status: int = MailStatus.UNREAD.value
    
    # 发件人
    sender_id: str = ""
    sender_name: str = ""
    
    # 收件人
    receiver_id: str = ""
    receiver_name: str = ""
    
    # 邮件内容
    title: str = ""
    content: str = ""
    
    # 附件
    attachment: Optional[MailAttachment] = None
    
    # 时间
    send_time: float = 0.0
    read_time: float = 0.0
    delete_time: float = 0.0
    
    # 过期时间（0表示永不过期）
    expire_time: float = 0.0
    
    def __post_init__(self):
        if not self.send_time:
            self.send_time = time.time()
    
    @property
    def is_read(self) -> bool:
        """是否已读"""
        return self.status == MailStatus.READ.value
    
    @property
    def is_deleted(self) -> bool:
        """是否已删除"""
        return self.status == MailStatus.DELETED.value
    
    @property
    def has_attachment(self) -> bool:
        """是否有附件"""
        return self.attachment is not None
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.expire_time <= 0:
            return False
        return time.time() > self.expire_time
    
    def mark_as_read(self) -> None:
        """标记为已读"""
        if self.status == MailStatus.UNREAD.value:
            self.status = MailStatus.READ.value
            self.read_time = time.time()
    
    def mark_as_deleted(self) -> None:
        """标记为已删除"""
        self.status = MailStatus.DELETED.value
        self.delete_time = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "mail_id": self.mail_id,
            "mail_type": self.mail_type,
            "status": self.status,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "receiver_id": self.receiver_id,
            "receiver_name": self.receiver_name,
            "title": self.title,
            "content": self.content,
            "attachment": self.attachment.to_dict() if self.attachment else None,
            "send_time": self.send_time,
            "read_time": self.read_time,
            "delete_time": self.delete_time,
            "expire_time": self.expire_time,
        }


class MailManager:
    """邮件管理器"""
    
    def __init__(self):
        # 所有邮件（mail_id -> Mail）
        self._mails: Dict[int, Mail] = {}
        
        # 用户收件箱（user_id -> [mail_id]）
        self._inboxes: Dict[str, List[int]] = {}
        
        # 用户发件箱（user_id -> [mail_id]）
        self._outboxes: Dict[str, List[int]] = {}
        
        # 邮件ID计数器
        self._mail_id_counter = 0
    
    def send_mail(
        self,
        sender_id: str,
        sender_name: str,
        receiver_id: str,
        receiver_name: str,
        title: str,
        content: str = "",
        mail_type: int = MailType.NORMAL.value,
        attachment: Optional[MailAttachment] = None,
        expire_days: int = 30,
    ) -> Optional[Mail]:
        """
        发送邮件
        
        Args:
            sender_id: 发件人ID
            sender_name: 发件人名称
            receiver_id: 收件人ID
            receiver_name: 收件人名称
            title: 邮件标题
            content: 邮件内容
            mail_type: 邮件类型
            attachment: 附件
            expire_days: 过期天数（0表示永不过期）
            
        Returns:
            发送的邮件对象
        """
        self._mail_id_counter += 1
        mail_id = self._mail_id_counter
        
        expire_time = 0.0
        if expire_days > 0:
            expire_time = time.time() + expire_days * 24 * 3600
        
        mail = Mail(
            mail_id=mail_id,
            mail_type=mail_type,
            sender_id=sender_id,
            sender_name=sender_name,
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            title=title,
            content=content,
            attachment=attachment,
            expire_time=expire_time,
        )
        
        self._mails[mail_id] = mail
        
        # 添加到收件箱
        if receiver_id not in self._inboxes:
            self._inboxes[receiver_id] = []
        self._inboxes[receiver_id].append(mail_id)
        
        # 添加到发件箱
        if sender_id not in self._outboxes:
            self._outboxes[sender_id] = []
        self._outboxes[sender_id].append(mail_id)
        
        logger.info(
            f"发送邮件: {sender_name} -> {receiver_name}, "
            f"标题={title}, 有附件={attachment is not None}"
        )
        
        return mail
    
    def send_system_mail(
        self,
        receiver_id: str,
        receiver_name: str,
        title: str,
        content: str = "",
        attachment: Optional[MailAttachment] = None,
        expire_days: int = 30,
    ) -> Optional[Mail]:
        """
        发送系统邮件
        
        Args:
            receiver_id: 收件人ID
            receiver_name: 收件人名称
            title: 邮件标题
            content: 邮件内容
            attachment: 附件
            expire_days: 过期天数
            
        Returns:
            发送的邮件对象
        """
        return self.send_mail(
            sender_id="system",
            sender_name="系统",
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            title=title,
            content=content,
            mail_type=MailType.SYSTEM.value,
            attachment=attachment,
            expire_days=expire_days,
        )
    
    def send_item_mail(
        self,
        receiver_id: str,
        receiver_name: str,
        item_id: int,
        item_name: str,
        count: int = 1,
        reinforce_level: int = 0,
        amplify_level: int = 0,
        amplify_type: str = "",
        sender_name: str = "系统",
        title: str = "",
        content: str = "",
    ) -> Optional[Mail]:
        """
        发送物品邮件
        
        Args:
            receiver_id: 收件人ID
            receiver_name: 收件人名称
            item_id: 物品ID
            item_name: 物品名称
            count: 数量
            reinforce_level: 强化等级
            amplify_level: 增幅等级
            amplify_type: 增幅类型
            sender_name: 发件人名称
            title: 邮件标题
            content: 邮件内容
            
        Returns:
            发送的邮件对象
        """
        if not title:
            title = f"获得物品：{item_name}"
        
        if not content:
            content = f"您获得了 {item_name} x{count}，请查收。"
        
        attachment = MailAttachment(
            item_id=item_id,
            item_name=item_name,
            count=count,
            reinforce_level=reinforce_level,
            amplify_level=amplify_level,
            amplify_type=amplify_type,
        )
        
        return self.send_mail(
            sender_id="system",
            sender_name=sender_name,
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            title=title,
            content=content,
            mail_type=MailType.SYSTEM.value,
            attachment=attachment,
        )
    
    def send_gold_mail(
        self,
        receiver_id: str,
        receiver_name: str,
        gold: int,
        sender_name: str = "系统",
        title: str = "",
        content: str = "",
    ) -> Optional[Mail]:
        """
        发送金币邮件
        
        Args:
            receiver_id: 收件人ID
            receiver_name: 收件人名称
            gold: 金币数量
            sender_name: 发件人名称
            title: 邮件标题
            content: 邮件内容
            
        Returns:
            发送的邮件对象
        """
        if not title:
            title = "获得金币"
        
        if not content:
            content = f"您获得了 {gold} 金币，请查收。"
        
        attachment = MailAttachment(gold=gold)
        
        return self.send_mail(
            sender_id="system",
            sender_name=sender_name,
            receiver_id=receiver_id,
            receiver_name=receiver_name,
            title=title,
            content=content,
            mail_type=MailType.SYSTEM.value,
            attachment=attachment,
        )
    
    def get_inbox(self, user_id: str, include_deleted: bool = False) -> List[Mail]:
        """
        获取收件箱
        
        Args:
            user_id: 用户ID
            include_deleted: 是否包含已删除邮件
            
        Returns:
            邮件列表（按发送时间倒序）
        """
        if user_id not in self._inboxes:
            return []
        
        mails = []
        for mail_id in self._inboxes[user_id]:
            mail = self._mails.get(mail_id)
            if not mail:
                continue
            if not include_deleted and mail.is_deleted:
                continue
            mails.append(mail)
        
        # 按发送时间倒序
        mails.sort(key=lambda m: m.send_time, reverse=True)
        
        return mails
    
    def get_outbox(self, user_id: str, include_deleted: bool = False) -> List[Mail]:
        """
        获取发件箱
        
        Args:
            user_id: 用户ID
            include_deleted: 是否包含已删除邮件
            
        Returns:
            邮件列表（按发送时间倒序）
        """
        if user_id not in self._outboxes:
            return []
        
        mails = []
        for mail_id in self._outboxes[user_id]:
            mail = self._mails.get(mail_id)
            if not mail:
                continue
            if not include_deleted and mail.is_deleted:
                continue
            mails.append(mail)
        
        # 按发送时间倒序
        mails.sort(key=lambda m: m.send_time, reverse=True)
        
        return mails
    
    def get_mail(self, mail_id: int) -> Optional[Mail]:
        """获取邮件"""
        return self._mails.get(mail_id)
    
    def read_mail(self, mail_id: int) -> Optional[Mail]:
        """
        阅读邮件（标记为已读）
        
        Args:
            mail_id: 邮件ID
            
        Returns:
            邮件对象
        """
        mail = self._mails.get(mail_id)
        if mail:
            mail.mark_as_read()
            logger.info(f"阅读邮件: {mail_id}, 标题={mail.title}")
        return mail
    
    def delete_mail(self, mail_id: int) -> bool:
        """
        删除邮件
        
        Args:
            mail_id: 邮件ID
            
        Returns:
            是否成功
        """
        mail = self._mails.get(mail_id)
        if not mail:
            return False
        
        mail.mark_as_deleted()
        logger.info(f"删除邮件: {mail_id}, 标题={mail.title}")
        return True
    
    def delete_mails(self, mail_ids: List[int]) -> int:
        """
        批量删除邮件
        
        Args:
            mail_ids: 邮件ID列表
            
        Returns:
            成功删除的数量
        """
        count = 0
        for mail_id in mail_ids:
            if self.delete_mail(mail_id):
                count += 1
        return count
    
    def claim_attachment(self, mail_id: int) -> Optional[MailAttachment]:
        """
        领取邮件附件
        
        Args:
            mail_id: 邮件ID
            
        Returns:
            附件对象（如果有）
        """
        mail = self._mails.get(mail_id)
        if not mail or not mail.attachment:
            return None
        
        attachment = mail.attachment
        mail.attachment = None
        
        # 标记为已读
        mail.mark_as_read()
        
        logger.info(
            f"领取邮件附件: {mail_id}, "
            f"物品={attachment.item_name}x{attachment.count}, "
            f"金币={attachment.gold}, 点券={attachment.cera}"
        )
        
        return attachment
    
    def get_unread_count(self, user_id: str) -> int:
        """获取未读邮件数量"""
        inbox = self.get_inbox(user_id)
        return sum(1 for mail in inbox if not mail.is_read)
    
    def get_attachment_count(self, user_id: str) -> int:
        """获取有附件的邮件数量"""
        inbox = self.get_inbox(user_id)
        return sum(1 for mail in inbox if mail.has_attachment)
    
    def cleanup_expired_mails(self) -> int:
        """
        清理过期邮件
        
        Returns:
            清理的邮件数量
        """
        expired_ids = []
        for mail_id, mail in self._mails.items():
            if mail.is_expired and not mail.is_deleted:
                expired_ids.append(mail_id)
        
        for mail_id in expired_ids:
            self.delete_mail(mail_id)
        
        if expired_ids:
            logger.info(f"清理过期邮件: {len(expired_ids)}封")
        
        return len(expired_ids)
    
    def to_dict(self, user_id: str) -> dict:
        """转换为字典"""
        inbox = self.get_inbox(user_id)
        outbox = self.get_outbox(user_id)
        
        return {
            "user_id": user_id,
            "inbox_count": len(inbox),
            "outbox_count": len(outbox),
            "unread_count": self.get_unread_count(user_id),
            "attachment_count": self.get_attachment_count(user_id),
            "inbox": [mail.to_dict() for mail in inbox],
            "outbox": [mail.to_dict() for mail in outbox],
        }
