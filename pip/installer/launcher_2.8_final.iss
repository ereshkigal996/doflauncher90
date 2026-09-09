; DNF轮回启动器 - 多功能安装程序
; 版本: 2.8
; 功能: 安装/更新/卸载，包含用户协议

#define MyAppName "DNF轮回启动器"
#define MyAppVersion "2.9.0"
#define MyAppPublisher "ereshkigal996"
#define MyAppExeName "launcher.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\DNFLauncher
DefaultGroupName=DNF Launcher
DisableProgramGroupPage=yes
OutputDir=C:\Users\56518\Downloads\doubao_work\release_2.9
OutputBaseFilename=launcher_2.9.0_beta1_release
SetupIconFile=C:\Users\56518\Downloads\doubao_work\pip_2.9\DFO.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\launcher.exe
UninstallDisplayName={#MyAppName}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} 多功能安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
LicenseFile=C:\Users\56518\Downloads\doubao_work\temp\installer_build_2.9\license.txt

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "C:\Users\56518\Downloads\doubao_work\temp\installer_build_2.9\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; 注意：backup和lib目录不在[UninstallDelete]中删除，改在[Code]段中根据用户选择处理
; 技术债务修复：完善卸载时的残留文件处理
[UninstallDelete]
Type: filesandordirs; Name: "{app}\config.lau"
Type: filesandordirs; Name: "{app}\config.lau.bak"
Type: filesandordirs; Name: "{app}\config.lau.corrupted"
Type: filesandordirs; Name: "{app}\acc.dat"
Type: filesandordirs; Name: "{app}\acc.dat.bak"
Type: filesandordirs; Name: "{app}\runtime.log"
Type: filesandordirs; Name: "{app}\error.log"
Type: filesandordirs; Name: "{app}\*.tmp"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
var
  { 多功能页面变量 }
  ActionPage: TInputOptionWizardPage;
  IsInstalled: Boolean;
  InstalledPath: String;

  { 卸载选项变量 }
  KeepBackup: Boolean;
  KeepLib: Boolean;

function IsAppInstalled(): Boolean;
var
  UninstallString: String;
begin
  Result := False;
  InstalledPath := '';

  { 检查注册表中的卸载信息 }
  if RegQueryStringValue(HKEY_LOCAL_MACHINE,
     'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1',
     'InstallLocation', InstalledPath) then
  begin
    Result := True;
  end
  else if RegQueryStringValue(HKEY_CURRENT_USER,
     'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}_is1',
     'InstallLocation', InstalledPath) then
  begin
    Result := True;
  end;

  { 检查常见安装路径 }
  if not Result then
  begin
    if DirExists(ExpandConstant('{autopf}\DNFLauncher')) then
    begin
      InstalledPath := ExpandConstant('{autopf}\DNFLauncher');
      if FileExists(InstalledPath + '\launcher.exe') then
        Result := True;
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;

  { 检测是否已安装 }
  IsInstalled := IsAppInstalled();
end;

procedure InitializeWizard();
begin
  if IsInstalled then
  begin
    { 创建操作选择页面（在许可协议页面之后） }
    ActionPage := CreateInputOptionPage(
      wpLicense,
      '选择操作',
      '检测到您的电脑中已安装DNF轮回启动器',
      '安装路径: ' + InstalledPath + #13#10 + #13#10 + '请选择要执行的操作：',
      True,
      False
    );

    ActionPage.Add('更新启动器（保留配置和数据）');
    ActionPage.Add('卸载启动器');
    ActionPage.Add('修复启动器（重新安装文件）');
    ActionPage.Values[0] := True;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ResultCode: Integer;
  UninstallExe: String;
begin
  Result := True;

  { 如果已安装且在操作选择页面 }
  if IsInstalled and Assigned(ActionPage) and (CurPageID = ActionPage.ID) then
  begin
    { 选择卸载 }
    if ActionPage.Values[1] then
    begin
      { 询问是否保留备份文件 }
      if MsgBox('卸载选项' + #13#10 + #13#10 +
                '是否保留用户备份文件 (backup 目录)？' + #13#10 + #13#10 +
                '点击"是"保留备份文件' + #13#10 +
                '点击"否"删除备份文件',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        KeepBackup := True;
      end
      else
      begin
        KeepBackup := False;
      end;

      { 询问是否保留库文件 }
      if MsgBox('卸载选项' + #13#10 + #13#10 +
                '是否保留库文件 (lib 目录)？' + #13#10 + #13#10 +
                '点击"是"保留库文件' + #13#10 +
                '点击"否"删除库文件',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        KeepLib := True;
      end
      else
      begin
        KeepLib := False;
      end;

      { 确认卸载 }
      if MsgBox('确认要卸载DNF轮回启动器吗？' + #13#10 + #13#10 +
                '安装路径: ' + InstalledPath,
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        { 执行卸载 }
        if InstalledPath <> '' then
        begin
          UninstallExe := InstalledPath + '\unins000.exe';
          if FileExists(UninstallExe) then
          begin
            Exec(UninstallExe, '', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);

            { 根据用户选择删除保留的文件 }
            if not KeepBackup then
            begin
              if DirExists(InstalledPath + '\backup') then
                DelTree(InstalledPath + '\backup', True, True, True);
            end;
            if not KeepLib then
            begin
              if DirExists(InstalledPath + '\lib') then
                DelTree(InstalledPath + '\lib', True, True, True);
            end;

            MsgBox('卸载完成！', mbInformation, MB_OK);
          end
          else
          begin
            { 未找到卸载程序，手动删除 }
            DelTree(InstalledPath, True, True, True);
            MsgBox('卸载完成！', mbInformation, MB_OK);
          end;
        end;

        Result := False;
      end
      else
      begin
        Result := False;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { 安装完成后创建backup目录 }
    if not DirExists(ExpandConstant('{app}\backup')) then
      CreateDir(ExpandConstant('{app}\backup'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  { 卸载程序本身的卸载逻辑（从开始菜单卸载时） }
  { 使用默认卸载逻辑，在[UninstallDelete]中定义 }
end;
