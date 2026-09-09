; DNF轮回启动器 - Inno Setup多功能安装脚本
; 版本: 2.9.6
; 模式: onedir + Inno Setup + 多功能版（安装/更新/卸载）

#define MyAppName "DNF轮回启动器"
#define MyAppVersion "2.9.6"
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
OutputDir=C:\Users\56518\Downloads\DBObject\release
OutputBaseFilename=DNFLauncher_2.9.6_release_installer
SetupIconFile=C:\Users\56518\Downloads\DBObject\pip\launcher\DFO.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
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
LicenseFile=C:\Users\56518\Downloads\DBObject\release\DNFLauncher\用户协议.txt
InfoBeforeFile=
InfoAfterFile=

; 不显示欢迎页面，使用自定义选择页面
DisableWelcomePage=yes

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
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\lib\*"; DestDir: "{app}\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core

; GM工具：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\module\gmtool.exe"; DestDir: "{app}\module"; Flags: ignoreversion; Components: gmtool
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\module\items.json"; DestDir: "{app}\module"; Flags: ignoreversion; Components: gmtool
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\module\lib\*"; DestDir: "{app}\module\lib"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: gmtool

; 账号管理工具：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\module\accmg.exe"; DestDir: "{app}\module"; Flags: ignoreversion; Components: accmg

; 说明文档：只在"安装所有组件"时安装
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\README.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\常见问题.md"; DestDir: "{app}"; Flags: ignoreversion; Components: docs
Source: "C:\Users\56518\Downloads\DBObject\release\DNFLauncher\用户协议.txt"; DestDir: "{app}"; Flags: ignoreversion; Components: docs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Code]
var
  SelectPage: TWizardPage;
  InstallRadio: TNewRadioButton;
  UpdateRadio: TNewRadioButton;
  UninstallRadio: TNewRadioButton;
  IsInstalled: Boolean;
  InstallPath: String;

{ Windows API 函数声明 }
function GetWindowLong(hWnd: HWND; nIndex: Integer): Longint;
  external 'GetWindowLongW@user32.dll stdcall';
function SetWindowLong(hWnd: HWND; nIndex: Integer; dwNewLong: Longint): Longint;
  external 'SetWindowLongW@user32.dll stdcall';
function SetWindowPos(hWnd: HWND; hWndInsertAfter: HWND; X: Integer; Y: Integer; cx: Integer; cy: Integer; uFlags: UINT): BOOL;
  external 'SetWindowPos@user32.dll stdcall';

const
  GWL_STYLE = -16;
  GWL_EXSTYLE = -20;
  WS_CAPTION = $00C00000;
  WS_THICKFRAME = $00040000;
  WS_BORDER = $00800000;
  WS_DLGFRAME = $00400000;
  WS_EX_WINDOWEDGE = $00000100;
  WS_EX_CLIENTEDGE = $00000200;
  SWP_FRAMECHANGED = $0020;
  SWP_NOMOVE = $0002;
  SWP_NOSIZE = $0001;
  SWP_NOZORDER = $0004;

procedure RemoveWindowBorder();
var
  WizardHandle: HWND;
  Style: Longint;
  ExStyle: Longint;
begin
  WizardHandle := WizardForm.Handle;
  
  { 移除窗口边框和标题栏 }
  Style := GetWindowLong(WizardHandle, GWL_STYLE);
  Style := Style and not WS_CAPTION;
  Style := Style and not WS_THICKFRAME;
  Style := Style and not WS_BORDER;
  Style := Style and not WS_DLGFRAME;
  SetWindowLong(WizardHandle, GWL_STYLE, Style);
  
  { 移除扩展窗口样式 }
  ExStyle := GetWindowLong(WizardHandle, GWL_EXSTYLE);
  ExStyle := ExStyle and not WS_EX_WINDOWEDGE;
  ExStyle := ExStyle and not WS_EX_CLIENTEDGE;
  SetWindowLong(WizardHandle, GWL_EXSTYLE, ExStyle);
  
  { 应用窗口样式更改 }
  SetWindowPos(WizardHandle, 0, 0, 0, 0, 0, SWP_FRAMECHANGED or SWP_NOMOVE or SWP_NOSIZE or SWP_NOZORDER);
end;

function IsAppInstalled(): Boolean;
var
  UninstallString: String;
begin
  Result := False;
  InstallPath := '';
  
  { 检查注册表中的卸载信息 }
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1', 'InstallLocation', InstallPath) then
  begin
    if InstallPath <> '' then
    begin
      if FileExists(InstallPath + '\launcher.exe') then
      begin
        Result := True;
      end;
    end;
  end;
  
  { 如果HKLM没有找到，检查HKCU }
  if not Result then
  begin
    if RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1', 'InstallLocation', InstallPath) then
    begin
      if InstallPath <> '' then
      begin
        if FileExists(InstallPath + '\launcher.exe') then
        begin
          Result := True;
        end;
      end;
    end;
  end;
end;

procedure InitializeWizard();
begin
  { 检查是否已安装 }
  IsInstalled := IsAppInstalled();
  
  { 创建选择页面 }
  SelectPage := CreateCustomPage(wpWelcome, '选择操作', '请选择您要执行的操作');
  
  { 安装选项 }
  InstallRadio := TNewRadioButton.Create(SelectPage.Surface);
  InstallRadio.Parent := SelectPage.Surface;
  InstallRadio.Left := ScaleX(20);
  InstallRadio.Top := ScaleY(20);
  InstallRadio.Width := ScaleX(300);
  InstallRadio.Height := ScaleY(25);
  InstallRadio.Caption := '安装 DNF轮回启动器';
  InstallRadio.Checked := True;
  
  { 更新选项（仅在已安装时显示） }
  if IsInstalled then
  begin
    UpdateRadio := TNewRadioButton.Create(SelectPage.Surface);
    UpdateRadio.Parent := SelectPage.Surface;
    UpdateRadio.Left := ScaleX(20);
    UpdateRadio.Top := ScaleY(55);
    UpdateRadio.Width := ScaleX(300);
    UpdateRadio.Height := ScaleY(25);
    UpdateRadio.Caption := '更新现有安装';
    UpdateRadio.Checked := False;
    
    { 卸载选项 }
    UninstallRadio := TNewRadioButton.Create(SelectPage.Surface);
    UninstallRadio.Parent := SelectPage.Surface;
    UninstallRadio.Left := ScaleX(20);
    UninstallRadio.Top := ScaleY(90);
    UninstallRadio.Width := ScaleX(300);
    UninstallRadio.Height := ScaleY(25);
    UninstallRadio.Caption := '卸载 DNF轮回启动器';
    UninstallRadio.Checked := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  UninstallExe: String;
  ResultCode: Integer;
begin
  Result := True;
  
  { 如果在选择页面，根据选择执行不同操作 }
  if CurPageID = SelectPage.ID then
  begin
    if Assigned(UninstallRadio) and UninstallRadio.Checked then
    begin
      { 执行卸载 }
      if IsInstalled then
      begin
        UninstallExe := InstallPath + '\unins000.exe';
        if FileExists(UninstallExe) then
        begin
          if MsgBox('确定要卸载 DNF轮回启动器 吗？', mbConfirmation, MB_YESNO) = IDYES then
          begin
            Exec(UninstallExe, '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
            Result := False;
          end
          else
          begin
            Result := False;
          end;
        end
        else
        begin
          MsgBox('未找到卸载程序！', mbError, MB_OK);
          Result := False;
        end;
      end;
    end
    else if Assigned(UpdateRadio) and UpdateRadio.Checked then
    begin
      { 更新模式：使用已安装的路径 }
      if IsInstalled then
      begin
        { 设置安装目录为已安装的目录 }
        WizardForm.DirEdit.Text := InstallPath;
      end;
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  { 如果是目录选择页面，并且是更新模式，禁用目录编辑 }
  if CurPageID = wpSelectDir then
  begin
    if Assigned(UpdateRadio) and UpdateRadio.Checked then
    begin
      WizardForm.DirEdit.Enabled := False;
      WizardForm.DirBrowseButton.Enabled := False;
    end
    else
    begin
      WizardForm.DirEdit.Enabled := True;
      WizardForm.DirBrowseButton.Enabled := True;
    end;
  end;
end;

