"""
拍卖行系统模块
实现DNF拍卖行数据模型、上架、购买、搜索、交易等
"""

import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


# 日志
logger = logging.getLogger(__name__)


# 拍卖状态
class AuctionStatus(Enum):
    """拍卖状态"""
    ON_SALE = 0        # 上架中
    SOLD = 1           # 已售出
    EXPIRED = 2        # 已过期
    CANCELLED = 3      # 已取消
    REMOVED = 4        # 已移除


# 物品类型过滤
class AuctionItemType(Enum):
    """拍卖行物品类型"""
    ALL = "all"                    # 全部
    EQUIPMENT = "equipment"        # 装备
    WEAPON = "weapon"              # 武器
    ARMOR = "armor"                # 防具
    ACCESSORY = "accessory"        # 首饰
    SPECIAL = "special"            # 特殊装备
    AVATAR = "avatar"              # 装扮
    CREATURE = "creature"          # 宠物
    TITLE = "title"                # 称号
    CONSUMABLE = "consumable"      # 消耗品
    MATERIAL = "material"          # 材料
    CARD = "card"                  # 卡片
    OTHER = "other"                # 其他


# 排序方式
class AuctionSortBy(Enum):
    """排序方式"""
    PRICE_ASC = "price_asc"            # 价格从低到高
    PRICE_DESC = "price_desc"          # 价格从高到低
    TIME_ASC = "time_asc"              # 时间从早到晚
    TIME_DESC = "time_desc"            # 时间从晚到早
    LEVEL_ASC = "level_asc"            # 等级从低到高
    LEVEL_DESC = "level_desc"          # 等级从高到低
    QUANTITY_ASC = "quantity_asc"      # 数量从少到多
    QUANTITY_DESC = "quantity_desc"    # 数量从多到少


@dataclass
class AuctionItem:
    """拍卖物品"""
    item_id: int = 0
    item_name: str = ""
    item_type: str = ""
    item_level: int = 0
    rarity: int = 0
    
    # 数量
    quantity: int = 1
    
    # 装备属性（仅装备类）
    reinforce_level: int = 0
    amplify_level: int = 0
    amplify_type: str = ""
    enchant_card_id: int = 0
    enchant_name: str = ""
    quality: int = 100
    
    # 额外属性
    extra_stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


@dataclass
class AuctionListing:
    """拍卖上架记录"""
    listing_id: int = 0
    seller_id: str = ""
    seller_name: str = ""
    
    # 物品信息
    item: AuctionItem = field(default_factory=AuctionItem)
    
    # 价格
    price: int = 0
    unit_price: int = 0  # 单价（用于显示）
    
    # 状态
    status: int = AuctionStatus.ON_SALE.value
    
    # 时间
    list_time: float = 0.0
    expire_time: float = 0.0
    sold_time: float = 0.0
    cancel_time: float = 0.0
    
    # 买家信息
    buyer_id: str = ""
    buyer_name: str = ""
    
    # 手续费
    deposit_fee: int = 0      # 上架押金
    transaction_fee: int = 0  # 交易手续费
    
    # 额外数据
    extra_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.list_time:
            self.list_time = time.time()
        if not self.expire_time:
            self.expire_time = self.list_time + 24 * 3600  # 默认24小时过期
    
    @property
    def is_on_sale(self) -> bool:
        """是否上架中"""
        return self.status == AuctionStatus.ON_SALE.value
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.status != AuctionStatus.ON_SALE.value:
            return False
        return time.time() > self.expire_time
    
    @property
    def remaining_time(self) -> float:
        """剩余时间（秒）"""
        if self.status != AuctionStatus.ON_SALE.value:
            return 0
        return max(0, self.expire_time - time.time())
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "listing_id": self.listing_id,
            "seller_id": self.seller_id,
            "seller_name": self.seller_name,
            "item": self.item.to_dict(),
            "price": self.price,
            "unit_price": self.unit_price,
            "status": self.status,
            "list_time": self.list_time,
            "expire_time": self.expire_time,
            "sold_time": self.sold_time,
            "cancel_time": self.cancel_time,
            "buyer_id": self.buyer_id,
            "buyer_name": self.buyer_name,
            "deposit_fee": self.deposit_fee,
            "transaction_fee": self.transaction_fee,
            "remaining_time": self.remaining_time,
        }


@dataclass
class AuctionTransaction:
    """拍卖交易记录"""
    transaction_id: int = 0
    listing_id: int = 0
    
    # 物品信息
    item_id: int = 0
    item_name: str = ""
    quantity: int = 1
    
    # 价格
    price: int = 0
    transaction_fee: int = 0
    seller_income: int = 0
    
    # 买卖双方
    seller_id: str = ""
    seller_name: str = ""
    buyer_id: str = ""
    buyer_name: str = ""
    
    # 时间
    transaction_time: float = 0.0
    
    def __post_init__(self):
        if not self.transaction_time:
            self.transaction_time = time.time()
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return asdict(self)


class AuctionManager:
    """拍卖行管理器"""
    
    def __init__(self):
        # 上架记录（listing_id -> AuctionListing）
        self._listings: Dict[int, AuctionListing] = {}
        
        # 交易记录（transaction_id -> AuctionTransaction）
        self._transactions: Dict[int, AuctionTransaction] = {}
        
        # 用户上架记录（user_id -> [listing_id]）
        self._user_listings: Dict[str, List[int]] = {}
        
        # 用户购买记录（user_id -> [transaction_id]）
        self._user_purchases: Dict[str, List[int]] = {}
        
        # 用户出售记录（user_id -> [transaction_id]）
        self._user_sales: Dict[str, List[int]] = {}
        
        # ID计数器
        self._listing_id_counter = 0
        self._transaction_id_counter = 0
        
        # 手续费配置
        self.deposit_fee_rate = 0.01    # 上架押金费率 1%
        self.transaction_fee_rate = 0.05  # 交易手续费率 5%
        self.max_deposit_fee = 100000    # 最高上架押金
        self.max_listing_duration = 72    # 最长上架时间（小时）
    
    def list_item(
        self,
        seller_id: str,
        seller_name: str,
        item: AuctionItem,
        price: int,
        duration_hours: int = 24,
    ) -> Tuple[bool, str, Optional[AuctionListing]]:
        """
        上架物品
        
        Args:
            seller_id: 卖家ID
            seller_name: 卖家名称
            item: 物品信息
            price: 总价
            duration_hours: 上架时长（小时）
            
        Returns:
            (是否成功, 原因, 上架记录)
        """
        # 验证价格
        if price <= 0:
            return False, "价格必须大于0", None
        
        # 验证数量
        if item.quantity <= 0:
            return False, "数量必须大于0", None
        
        # 验证上架时长
        if duration_hours <= 0 or duration_hours > self.max_listing_duration:
            return False, f"上架时长必须在1-{self.max_listing_duration}小时之间", None
        
        # 计算押金
        deposit_fee = min(int(price * self.deposit_fee_rate), self.max_deposit_fee)
        
        # 创建上架记录
        self._listing_id_counter += 1
        listing = AuctionListing(
            listing_id=self._listing_id_counter,
            seller_id=seller_id,
            seller_name=seller_name,
            item=item,
            price=price,
            unit_price=price // item.quantity if item.quantity > 0 else price,
            status=AuctionStatus.ON_SALE.value,
            list_time=time.time(),
            expire_time=time.time() + duration_hours * 3600,
            deposit_fee=deposit_fee,
        )
        
        # 保存记录
        self._listings[listing.listing_id] = listing
        
        if seller_id not in self._user_listings:
            self._user_listings[seller_id] = []
        self._user_listings[seller_id].append(listing.listing_id)
        
        logger.info(
            f"玩家{seller_name}上架物品: {item.item_name} x{item.quantity}, "
            f"价格: {price}, 押金: {deposit_fee}"
        )
        
        return True, "", listing
    
    def buy_item(
        self,
        listing_id: int,
        buyer_id: str,
        buyer_name: str,
        buyer_gold: int,
    ) -> Tuple[bool, str, Optional[AuctionTransaction]]:
        """
        购买物品
        
        Args:
            listing_id: 上架记录ID
            buyer_id: 买家ID
            buyer_name: 买家名称
            buyer_gold: 买家金币
            
        Returns:
            (是否成功, 原因, 交易记录)
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return False, "上架记录不存在", None
        
        if not listing.is_on_sale:
            return False, "该物品已下架或已售出", None
        
        if listing.is_expired:
            listing.status = AuctionStatus.EXPIRED.value
            return False, "该物品已过期", None
        
        # 检查是否是自己的物品
        if listing.seller_id == buyer_id:
            return False, "不能购买自己上架的物品", None
        
        # 检查金币是否足够
        if buyer_gold < listing.price:
            return False, f"金币不足，需要{listing.price}金币", None
        
        # 计算手续费
        transaction_fee = int(listing.price * self.transaction_fee_rate)
        seller_income = listing.price - transaction_fee
        
        # 创建交易记录
        self._transaction_id_counter += 1
        transaction = AuctionTransaction(
            transaction_id=self._transaction_id_counter,
            listing_id=listing_id,
            item_id=listing.item.item_id,
            item_name=listing.item.item_name,
            quantity=listing.item.quantity,
            price=listing.price,
            transaction_fee=transaction_fee,
            seller_income=seller_income,
            seller_id=listing.seller_id,
            seller_name=listing.seller_name,
            buyer_id=buyer_id,
            buyer_name=buyer_name,
        )
        
        # 保存交易记录
        self._transactions[transaction.transaction_id] = transaction
        
        # 更新上架记录状态
        listing.status = AuctionStatus.SOLD.value
        listing.sold_time = time.time()
        listing.buyer_id = buyer_id
        listing.buyer_name = buyer_name
        listing.transaction_fee = transaction_fee
        
        # 保存用户交易记录
        if buyer_id not in self._user_purchases:
            self._user_purchases[buyer_id] = []
        self._user_purchases[buyer_id].append(transaction.transaction_id)
        
        if listing.seller_id not in self._user_sales:
            self._user_sales[listing.seller_id] = []
        self._user_sales[listing.seller_id].append(transaction.transaction_id)
        
        logger.info(
            f"玩家{buyer_name}购买物品: {listing.item.item_name} x{listing.item.quantity}, "
            f"价格: {listing.price}, 手续费: {transaction_fee}, 卖家收入: {seller_income}"
        )
        
        return True, "", transaction
    
    def cancel_listing(
        self,
        listing_id: int,
        user_id: str,
    ) -> Tuple[bool, str]:
        """
        取消上架
        
        Args:
            listing_id: 上架记录ID
            user_id: 用户ID
            
        Returns:
            (是否成功, 原因)
        """
        listing = self._listings.get(listing_id)
        if not listing:
            return False, "上架记录不存在"
        
        if not listing.is_on_sale:
            return False, "该物品已下架或已售出"
        
        if listing.seller_id != user_id:
            return False, "只能取消自己上架的物品"
        
        # 更新状态
        listing.status = AuctionStatus.CANCELLED.value
        listing.cancel_time = time.time()
        
        logger.info(f"玩家取消上架: {listing.item.item_name}")
        
        return True, ""
    
    def get_listing(self, listing_id: int) -> Optional[AuctionListing]:
        """获取上架记录"""
        return self._listings.get(listing_id)
    
    def get_on_sale_listings(self) -> List[AuctionListing]:
        """获取所有上架中的物品"""
        # 先清理过期物品
        self._cleanup_expired()
        
        return [
            listing for listing in self._listings.values()
            if listing.is_on_sale
        ]
    
    def search_listings(
        self,
        keyword: str = "",
        item_type: str = AuctionItemType.ALL.value,
        min_level: int = 0,
        max_level: int = 100,
        min_price: int = 0,
        max_price: int = 0,
        rarity: int = -1,
        sort_by: str = AuctionSortBy.TIME_DESC.value,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[AuctionListing], int]:
        """
        搜索上架物品
        
        Args:
            keyword: 关键词
            item_type: 物品类型
            min_level: 最低等级
            max_level: 最高等级
            min_price: 最低价格
            max_price: 最高价格（0表示不限制）
            rarity: 稀有度（-1表示不限制）
            sort_by: 排序方式
            page: 页码
            page_size: 每页数量
            
        Returns:
            (物品列表, 总数)
        """
        listings = self.get_on_sale_listings()
        
        # 关键词过滤
        if keyword:
            keyword_lower = keyword.lower()
            listings = [
                l for l in listings
                if keyword_lower in l.item.item_name.lower()
                or keyword_lower in str(l.item.item_id)
            ]
        
        # 物品类型过滤
        if item_type != AuctionItemType.ALL.value:
            listings = [l for l in listings if l.item.item_type == item_type]
        
        # 等级过滤
        listings = [
            l for l in listings
            if min_level <= l.item.item_level <= max_level
        ]
        
        # 价格过滤
        if min_price > 0:
            listings = [l for l in listings if l.price >= min_price]
        if max_price > 0:
            listings = [l for l in listings if l.price <= max_price]
        
        # 稀有度过滤
        if rarity >= 0:
            listings = [l for l in listings if l.item.rarity == rarity]
        
        # 排序
        sort_functions = {
            AuctionSortBy.PRICE_ASC.value: lambda l: l.price,
            AuctionSortBy.PRICE_DESC.value: lambda l: -l.price,
            AuctionSortBy.TIME_ASC.value: lambda l: l.list_time,
            AuctionSortBy.TIME_DESC.value: lambda l: -l.list_time,
            AuctionSortBy.LEVEL_ASC.value: lambda l: l.item.item_level,
            AuctionSortBy.LEVEL_DESC.value: lambda l: -l.item.item_level,
            AuctionSortBy.QUANTITY_ASC.value: lambda l: l.item.quantity,
            AuctionSortBy.QUANTITY_DESC.value: lambda l: -l.item.quantity,
        }
        
        sort_func = sort_functions.get(sort_by, lambda l: -l.list_time)
        listings.sort(key=sort_func)
        
        # 分页
        total = len(listings)
        start = (page - 1) * page_size
        end = start + page_size
        listings = listings[start:end]
        
        return listings, total
    
    def get_user_listings(
        self,
        user_id: str,
        include_sold: bool = False,
        include_expired: bool = False,
    ) -> List[AuctionListing]:
        """获取用户上架记录"""
        listing_ids = self._user_listings.get(user_id, [])
        listings = [self._listings[lid] for lid in listing_ids if lid in self._listings]
        
        if not include_sold:
            listings = [l for l in listings if l.status != AuctionStatus.SOLD.value]
        if not include_expired:
            listings = [l for l in listings if l.status != AuctionStatus.EXPIRED.value]
        
        return listings
    
    def get_user_purchases(self, user_id: str) -> List[AuctionTransaction]:
        """获取用户购买记录"""
        transaction_ids = self._user_purchases.get(user_id, [])
        return [self._transactions[tid] for tid in transaction_ids if tid in self._transactions]
    
    def get_user_sales(self, user_id: str) -> List[AuctionTransaction]:
        """获取用户出售记录"""
        transaction_ids = self._user_sales.get(user_id, [])
        return [self._transactions[tid] for tid in transaction_ids if tid in self._transactions]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取拍卖行统计信息"""
        on_sale = self.get_on_sale_listings()
        
        total_value = sum(l.price for l in on_sale)
        total_items = sum(l.item.quantity for l in on_sale)
        
        # 按类型统计
        type_stats = {}
        for listing in on_sale:
            item_type = listing.item.item_type or "other"
            if item_type not in type_stats:
                type_stats[item_type] = {"count": 0, "value": 0}
            type_stats[item_type]["count"] += 1
            type_stats[item_type]["value"] += listing.price
        
        return {
            "on_sale_count": len(on_sale),
            "total_value": total_value,
            "total_items": total_items,
            "total_transactions": len(self._transactions),
            "type_stats": type_stats,
        }
    
    def _cleanup_expired(self) -> int:
        """清理过期物品"""
        expired_count = 0
        for listing in self._listings.values():
            if listing.is_on_sale and listing.is_expired:
                listing.status = AuctionStatus.EXPIRED.value
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"清理过期上架物品: {expired_count}个")
        
        return expired_count
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "listings_count": len(self._listings),
            "transactions_count": len(self._transactions),
            "on_sale_count": len(self.get_on_sale_listings()),
            "statistics": self.get_statistics(),
        }
