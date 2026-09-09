# GameServer 服务端 Python 实现

基于 DNF90-external-oneclick 服务端架构，使用 Python 重新实现的单机版服务端。

## 版本信息

- **当前版本**: 0.1.0 (开发中)
- **作者**: ereshkigal996
- **基于**: DNF90-external-oneclick 服务端架构
- **开发语言**: Python 3.8+

## 项目结构

```
game_server_python/
├── main.py                 # 主入口文件
├── __init__.py             # 包初始化
├── config/                 # 配置管理模块
│   ├── __init__.py
│   └── instance.py         # instance.json配置解析和管理
├── database/               # 数据库管理模块
│   ├── __init__.py
│   └── db_manager.py       # 数据库管理器（MySQL/SQLite双模式）
├── network/                # 网络服务模块
│   ├── __init__.py
│   └── base_server.py      # 基础TCP服务器（频道/管理监听）
├── pvf/                    # PVF文件解析模块
│   ├── __init__.py
│   └── pvf_parser.py       # PVF文件解析器和缓存管理
├── game/                   # 游戏逻辑模块
│   ├── __init__.py
│   └── account.py          # 账号管理（登录/注册/会话）
├── utils/                  # 工具模块
│   ├── __init__.py
│   ├── logger.py           # 日志记录器
│   └── process.py          # 进程管理器
└── data/                   # 数据目录
    ├── config/             # 配置文件
    │   └── instance.example.json  # 配置模板
    ├── logs/               # 日志文件
    └── state/              # 运行时状态
```

## 已实现功能

### 1. 配置管理 (config/instance.py)
- ✅ instance.json配置文件解析
- ✅ 服务端、数据库、游戏、协议、客户端配置管理
- ✅ 配置文件SHA256校验
- ✅ 配置保存功能
- ✅ MySQL DSN连接字符串生成

### 2. 数据库管理 (database/db_manager.py)
- ✅ MySQL和SQLite双模式支持
- ✅ 数据库连接池管理
- ✅ 线程安全的数据库操作
- ✅ 账号查询和验证
- ✅ 角色查询
- ✅ 表前缀支持
- ✅ 上下文管理器游标

### 3. 网络服务 (network/base_server.py)
- ✅ 基础TCP服务器
- ✅ 频道服务器（7001端口）
- ✅ 管理服务器（18111端口）
- ✅ 客户端连接管理
- ✅ 数据接收和发送
- ✅ 广播功能
- ✅ 连接回调（连接/断开/数据接收）
- ✅ 管理令牌验证

### 4. PVF文件解析 (pvf/pvf_parser.py)
- ✅ PVF文件加载
- ✅ 文件头解析
- ✅ 文件索引管理
- ✅ 文件内容读取
- ✅ 文本文件读取（多编码支持）
- ✅ 文件存在检查
- ✅ 文件列表和搜索
- ✅ 数据块缓存
- ✅ 文本缓存

### 5. 账号管理 (game/account.py)
- ✅ 账号登录验证
- ✅ 账号注册
- ✅ 密码哈希（bcrypt/简单哈希）
- ✅ 登录会话管理
- ✅ 会话令牌生成
- ✅ 会话验证和过期清理
- ✅ 在线账号统计
- ✅ 最后登录时间更新

### 6. 日志工具 (utils/logger.py)
- ✅ 多级日志（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- ✅ 控制台输出（带颜色）
- ✅ 文件输出（按日期分割）
- ✅ 线程安全
- ✅ 日志级别过滤

### 7. 进程管理 (utils/process.py)
- ✅ 进程启动/停止
- ✅ 进程状态监控
- ✅ 优雅终止和强制终止
- ✅ 进程超时处理
- ✅ 标准输出/错误重定向
- ✅ 进程状态文件保存
- ✅ 多进程管理

## 待实现功能

### 高优先级
- ⏳ 游戏协议解析和处理
- ⏳ 角色创建和管理
- ⏳ 游戏逻辑处理
- ⏳ 物品系统
- ⏳ 技能系统
- ⏳ 副本系统

### 中优先级
- ⏳ PVF文件完整解析
- ⏳ 频道系统
- ⏳ 队伍系统
- ⏳ 公会系统
- ⏳ 邮件系统
- ⏳ 交易系统

### 低优先级
- ⏳ Web管理界面
- ⏳ API接口
- ⏳ 性能监控
- ⏳ 自动更新
- ⏳ 插件系统

## 安装依赖

```bash
# 基础依赖
pip install pymysql bcrypt

# 可选依赖（用于性能优化）
pip install python-snappy lz4
```

## 使用方法

### 1. 准备配置文件

```bash
# 复制配置模板
cp data/config/instance.example.json data/config/instance.json

# 编辑配置文件
# 修改数据库模式、路径、端口等
```

### 2. 启动服务端

```bash
# 使用默认配置
python main.py

# 指定配置文件
python main.py -c /path/to/instance.json

# 调试模式
python main.py --debug

# 显示版本信息
python main.py -v
```

### 3. 命令行参数

- `-c, --config`: 指定配置文件路径
- `-v, --version`: 显示版本信息
- `--debug`: 调试模式

## 配置说明

### 数据库模式

#### SQLite模式（默认）
```json
{
  "database": {
    "mode": "sqlite",
    "path": "data/dnf90.db"
  }
}
```

#### MySQL模式
```json
{
  "database": {
    "mode": "mysql",
    "host": "127.0.0.1",
    "port": 13306,
    "name": "dnf_local",
    "user": "root",
    "password": "your_password"
  }
}
```

### 网络配置

```json
{
  "server": {
    "channelListen": "127.0.0.1:7001",
    "adminListen": "127.0.0.1:18111",
    "adminToken": "your_admin_token"
  }
}
```

## 开发说明

### 代码规范
- 遵循PEP 8代码规范
- 使用类型注解
- 使用dataclass定义数据结构
- 线程安全设计

### 模块依赖关系
```
main.py
├── config.instance (配置管理)
├── database.db_manager (数据库管理)
├── network.base_server (网络服务)
├── pvf.pvf_parser (PVF解析)
├── game.account (账号管理)
├── utils.logger (日志工具)
└── utils.process (进程管理)
```

### 全局单例模式
每个核心模块都提供全局单例：
- `get_config_manager()` - 获取配置管理器
- `get_db_manager()` - 获取数据库管理器
- `get_network_manager()` - 获取网络管理器
- `get_pvf_cache_manager()` - 获取PVF缓存管理器
- `get_account_manager()` - 获取账号管理器
- `get_logger()` - 获取日志记录器
- `get_process_manager()` - 获取进程管理器

## 参考项目

- [DNF90-external-oneclick](https://github.com/) - 原版服务端
- [dnf90-source-oneclick](https://github.com/) - 开源版服务端源码
- [pvfUtility](https://github.com/) - PVF文件解析工具

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

## 免责声明

1. 本软件仅供学习和研究使用，请勿用于商业用途。
2. 本软件为DNF单机版服务端，不包含任何游戏本体文件。
3. 使用本软件产生的一切后果由使用者自行承担。
4. 请尊重游戏版权，支持正版游戏。
5. 本软件免费发布，任何人不得将其用于商业盈利。

---

**感谢使用 GameServer 服务端 Python 实现！**
