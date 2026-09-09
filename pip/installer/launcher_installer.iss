; DNF轮回启动器 - Inno Setup安装脚本
; 版本: 2.9.1
; 模式: onedir + Inno Setup

#define MyAppName "DNF轮回启动器"
#define MyAppVersion "2.9.1"
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
OutputDir=C:\Users\56518\Downloads\doubao_work\release_2.0
OutputBaseFilename=launcher_2.9.1_release_install
SetupIconFile=C:\Users\56518\Downloads\doubao_work\pip_2.0\DFO.ico
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
LicenseFile=C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\用户协议.txt
InfoBeforeFile=
InfoAfterFile=

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Types]
Name: "full"; Description: "安装所有组件（含账号管理工具和文档）"
Name: "launcheronly"; Description: "只安装登录器"

[Components]
Name: "core"; Description: "登录器核心组件"; Types: full launcheronly; Flags: fixed
Name: "optional"; Description: "账号管理工具和文档"; Types: full

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked
Name: "quicklaunchicon"; Description: "创建快速启动栏快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Dirs]
Name: "{app}\module"

[Files]
; 核心组件：所有类型都安装
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; 可选组件：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\accmg.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: optional
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: optional
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\常见问题.md"; DestDir: "{app}"; Flags: ignoreversion; Components: optional
Source: "C:\Users\56518\Downloads\doubao_work\release_2.0\launcher\用户协议.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: optional

[Icons]
; 开始菜单
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载"; Filename: "{app}\uninstall.exe"

; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 快速启动栏
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; 安装完成后不自动运行程序
; [Run]段已移除

[UninstallDelete]
; 卸载时删除配置文件
Type: filesandordirs; Name: "{app}\launcher.json"
Type: filesandordirs; Name: "{app}\run.log"
Type: filesandordirs; Name: "{app}\error.log"
Type: filesandordirs; Name: "{app}\backup"

[Code]
var
  IsInstalled: Boolean;
  InstalledPath: String;
  ActionPage: TWizardPage;
  RadioInstall: TRadioButton;
  RadioUpdate: TRadioButton;
  RadioUninstall: TRadioButton;
  lblInstalledInfo: TLabel;

function GetUninstallString(): String;
var
  regPath: String;
begin
  regPath := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1';
  if RegQueryStringValue(HKLM, regPath, 'UninstallString', Result) then
    Result := RemoveQuotes(Result)
  else if RegQueryStringValue(HKCU, regPath, 'UninstallString', Result) then
    Result := RemoveQuotes(Result)
  else
    Result := '';
end;

function GetInstallLocation(): String;
var
  regPath: String;
begin
  regPath := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1';
  if not RegQueryStringValue(HKLM, regPath, 'InstallLocation', Result) then
    RegQueryStringValue(HKCU, regPath, 'InstallLocation', Result);
end;

procedure InitializeWizard();
begin
  // 检测是否已安装
  IsInstalled := (GetUninstallString() <> '');
  if IsInstalled then
    InstalledPath := GetInstallLocation();
  
  // 创建操作选择页面（在欢迎页之后）
  ActionPage := CreateCustomPage(wpWelcome, '选择操作', '请选择要执行的操作');
  
  // 已安装信息标签
  lblInstalledInfo := TLabel.Create(ActionPage);
  lblInstalledInfo.Parent := ActionPage.Surface;
  lblInstalledInfo.Left := 0;
  lblInstalledInfo.Top := 0;
  lblInstalledInfo.Font.Size := 10;
  lblInstalledInfo.Font.Color := clGray;
  
  if IsInstalled then
    lblInstalledInfo.Caption := '检测到已安装版本，安装路径: ' + InstalledPath
  else
    lblInstalledInfo.Caption := '未检测到已安装版本';
  
  // 安装选项
  RadioInstall := TRadioButton.Create(ActionPage);
  RadioInstall.Parent := ActionPage.Surface;
  RadioInstall.Left := 20;
  RadioInstall.Top := 40;
  RadioInstall.Width := 300;
  RadioInstall.Caption := '安装 DNF轮回启动器';
  RadioInstall.Checked := not IsInstalled;
  RadioInstall.Enabled := True;
  
  // 更新选项
  RadioUpdate := TRadioButton.Create(ActionPage);
  RadioUpdate.Parent := ActionPage.Surface;
  RadioUpdate.Left := 20;
  RadioUpdate.Top := 70;
  RadioUpdate.Width := 300;
  RadioUpdate.Caption := '更新到最新版本';
  RadioUpdate.Checked := IsInstalled;
  RadioUpdate.Enabled := IsInstalled;
  
  // 卸载选项
  RadioUninstall := TRadioButton.Create(ActionPage);
  RadioUninstall.Parent := ActionPage.Surface;
  RadioUninstall.Left := 20;
  RadioUninstall.Top := 100;
  RadioUninstall.Width := 300;
  RadioUninstall.Caption := '卸载当前版本';
  RadioUninstall.Enabled := IsInstalled;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  uninstallStr: String;
  ResultCode: Integer;
begin
  Result := True;
  
  // 在操作选择页面点击下一步
  if CurPageID = ActionPage.ID then
  begin
    // 如果选择卸载
    if RadioUninstall.Checked and IsInstalled then
    begin
      uninstallStr := GetUninstallString();
      if uninstallStr <> '' then
      begin
        // 执行卸载程序
        Exec(uninstallStr, '', '', SW_SHOWNORMAL, ewWaitUntilTerminated, ResultCode);
      end;
      // 退出安装程序
      Result := False;
      exit;
    end;
    
    // 如果选择安装或更新，继续安装流程
    Result := True;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  oldUninstall: String;
  newUninstall: String;
begin
  if CurStep = ssPostInstall then
  begin
    // 创建backup文件夹
    if not DirExists(ExpandConstant('{app}\backup')) then
      CreateDir(ExpandConstant('{app}\backup'));
    
    // 重命名卸载程序为uninstall.exe
    oldUninstall := ExpandConstant('{app}\unins000.exe');
    newUninstall := ExpandConstant('{app}\uninstall.exe');
    if FileExists(oldUninstall) then
    begin
      if FileExists(newUninstall) then
        DeleteFile(newUninstall);
      RenameFile(oldUninstall, newUninstall);
    end;
  end;
end;
