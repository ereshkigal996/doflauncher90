; DNF轮回启动器 - Inno Setup安装脚本
; 版本: 2.9.5
; 模式: onedir + Inno Setup

#define MyAppName "DNF轮回启动器"
#define MyAppVersion "2.9.5"
#define MyAppPublisher "ereshkigal996"
#define MyAppExeName "launcher.exe"
#define MyAppAssocName "DNF轮回启动器"
#define MyAppAssocExt ".dnf"
#define MyAppURL "https://github.com/ereshkigal996"

[Setup]
; 应用程序基本信息
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装目录（全英文）
DefaultDirName={autopf}\DNFLauncher
DefaultGroupName=DNF Launcher

; 安装选项
DisableProgramGroupPage=yes
OutputDir=C:\Users\56518\Downloads\doubao_work\release
OutputBaseFilename=launcher_2.9.5_release_install
SetupIconFile=C:\Users\56518\Downloads\doubao_work\pip\DFO.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
UninstallDisplayIcon={app}\launcher.exe
UninstallDisplayName=uninstall
UninstallFilesDir={app}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

; 安装界面
LicenseFile=C:\Users\56518\Downloads\doubao_work\release\launcher\用户协议.txt
InfoBeforeFile=
InfoAfterFile=

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Types]
Name: "full"; Description: "安装所有组件（含GM工具、账号管理工具和文档）"
Name: "launcheronly"; Description: "只安装登录器"

[Components]
Name: "core"; Description: "登录器核心组件"; Types: full launcheronly; Flags: fixed
Name: "gmtool"; Description: "GM工具"; Types: full
Name: "accmg"; Description: "账号管理工具"; Types: full
Name: "docs"; Description: "说明文档"; Types: full

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Dirs]
Name: "{app}\module"
Name: "{app}\backup"
Name: "{app}\temp"

[Files]
; 核心组件：所有类型都安装
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; GM工具：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\module\gmtool.exe"; DestDir: "{app}\module"; Flags: ignoreversion; Components: gmtool
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\module\items.json"; DestDir: "{app}\module"; Flags: ignoreversion; Components: gmtool

; 账号管理工具：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\module\accmg.exe"; DestDir: "{app}\module"; Flags: ignoreversion; Components: accmg

; 说明文档：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\常见问题.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs
Source: "C:\Users\56518\Downloads\doubao_work\release\launcher\用户协议.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: docs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
