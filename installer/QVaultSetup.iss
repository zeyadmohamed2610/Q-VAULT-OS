; Q-VAULT OS Installer Script
; Inno Setup Script for Q-VAULT OS v1.2.0

#define MyAppName = 'Q-VAULT OS'
#define MyAppVersion = '1.2.0'
#define MyAppPublisher = 'Q-VAULT Systems'
#define MyAppURL = 'https://qvault-os.com'
#define MyAppExeName = 'Q-VAULT OS.exe'

[Setup]
AppId={{A8F7E9C2-4B3D-5A1E-9F8C-7D6E5C4B3A2F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\/LICENSE
OutputDir=..\bin
OutputBaseFilename=QVaultOS-Setup-{#MyAppVersion}
SetupIconFile=..\resources\/icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64

[Languages]
Name: 'english'; MessagesFile: 'compiler:Default.isl'

[Tasks]
Name: 'desktopicon'; Description: '{cm:CreateDesktopIcon}'; GroupDescription: '{cm:AdditionalIcons}';
Name: 'quicklaunchicon'; Description: '{cm:CreateQuickLaunchIcon}'; GroupDescription: '{cm:AdditionalIcons}';
Name: 'autostart'; Description: 'Start Q-VAULT OS when Windows starts'; GroupDescription: 'Startup:';
Name: 'associate_files'; Description: 'Associate .vault files with Q-VAULT OS'; GroupDescription: 'File Associations:';

[Files]
Source: '..\bin\release\/*'; DestDir: '{app}'; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: '{group}\\{#MyAppName}'; Filename: '{app}\\{#MyAppExeName}'
Name: '{group}\\{cm:UninstallProgram,{#MyAppName}}'; Filename: '{uninstallexe}'
Name: '{autodesktop}\\{#MyAppName}'; Filename: '{app}\\{#MyAppExeName}'; Tasks: desktopicon
Name: '{userappdata}\\Microsoft\ternet Explorer\rite List\\{#MyAppName}'; Filename: '{app}\\{#MyAppExeName}'; Tasks: quicklaunchicon

[Registry]
Root: HKCU; Subkey: 'Software\\Microsoft\/windows\run'; ValueType: string; ValueName: 'Q-VAULT OS'; ValueData: '{app}\\{#MyAppExeName} --autostart'; Flags: uninsdeletevalue; Tasks: autostart

Root: HKCR; Subkey: '.vault'; ValueType: string; ValueData: 'QVAULTFile'; Flags: uninsdeletekey; Tasks: associate_files
Root: HKCR; Subkey: 'QVAULTFile'; ValueType: string; ValueData: 'Q-VAULT Secure File'; Flags: uninsdeletekey; Tasks: associate_files
Root: HKCR; Subkey: 'QVAULTFile\file'; ValueType: string; ValueData: '{app}\\{#MyAppExeName} --open %1'; Tasks: associate_files

[Run]
Filename: '{app}\\{#MyAppExeName}'; Description: '{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}'; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: '{userappdata}\\.qvault'

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-installation tasks
  end;
end;