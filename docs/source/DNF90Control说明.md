# DNF90 Python版控制器

这是DNF90服务端控制器的Python实现，对应原版的`DNF90Control.exe`。

## 功能特性

- ✅ 项目根目录自动发现
- ✅ 服务端启动/停止/状态查询
- ✅ 便携版MySQL管理（启动/停止/初始化/健康检查）
- ✅ 账号管理（注册/登录/列表）
- ✅ 客户端启动
- ✅ 环境检查
- ✅ 进程管理（Windows）
- ✅ 配置文件读写

## 项目结构

```
dnf90_control_py/
├── main.py              # 主入口，CLI命令解析
├── core/
│   ├── paths.py         # 路径发现和项目根目录识别
│   ├── config.py        # 配置管理（instance.json）
│   └── controller.py    # 主控制器，核心业务逻辑
├── modules/
│   ├── process_manager.py   # Windows进程管理
│   ├── mysql_manager.py     # 便携版MySQL管理
│   └── account_manager.py   # 账号注册/登录/列表
└── utils/
```

## 安装依赖

```bash
pip install bcrypt
```

## 使用方法

### 启动服务端
```bash
python main.py start
python main.py start --rebuild
```

### 停止服务端
```bash
python main.py stop
python main.py stop --keep-database
```

### 查看状态
```bash
python main.py status
```

### 环境检查
```bash
python main.py check
python main.py check --skip-database
python main.py check --skip-ports
python main.py check --client
```

### 启动客户端
```bash
python main.py launch-client --client-directory "C:\Games\DNF"
python main.py launch-client --multi-instance
python main.py launch-client --username test --password-stdin
```

### 账号管理
```bash
# 注册账号
echo "password123" | python main.py account register --username test --password-stdin

# 登录验证
echo "password123" | python main.py account login --username test --password-stdin

# 列出所有账号
python main.py account list
```

## 项目根目录识别

控制器会自动查找DNF90项目根目录，识别标准是同时存在以下两个文件：
1. `runtime/templates/instance.example.json`
2. `runtime/assets/manifest.json`

查找顺序：
1. 环境变量 `DNF90_PROJECT_ROOT`
2. 当前工作目录向上查找
3. 可执行文件所在目录向上查找

## 与原版的区别

| 功能 | 原版(Go) | Python版 |
|------|----------|----------|
| 服务端启动/停止 | ✅ | ✅ |
| MySQL管理 | ✅ | ✅ |
| 账号管理 | ✅ | ✅ |
| 客户端启动 | ✅ | ✅ |
| 环境检查 | ✅ | ✅ |
| 二进制编译 | ✅ | ❌（需要Go环境） |
| 命令锁 | ✅ | ⚠️（简化实现） |
| 中断恢复 | ✅ | ⚠️（简化实现） |

## 注意事项

1. 本版本为开发中的实现，部分功能可能不完整
2. 密码加密使用bcrypt，需要安装`bcrypt`库
3. 仅支持Windows平台（进程管理使用Windows API）
4. 建议在原版控制器的项目目录中使用

## 许可证

仅供学习和研究使用。
