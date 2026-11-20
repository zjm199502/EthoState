[Setup]
AppId={{79209F20-7EA6-47F8-928A-FDFE1CC68FB3}
AppName=EthoState
AppVersion=1.0.1
AppPublisher=EthoState contributors
AppPublisherURL=https://github.com/zjm199502/EthoState
DefaultDirName={localappdata}\Programs\EthoState
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
OutputDir=release
OutputBaseFilename=EthoState-1.0.1-Windows-x64-Setup
Compression=lzma2/fast
SolidCompression=yes
SetupIconFile=ethostate.ico
UninstallDisplayIcon={app}\EthoState.exe
WizardStyle=modern
[Files]
Source: "dist\EthoState\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\EthoState"; Filename: "{app}\EthoState.exe"
[Run]
Filename: "{app}\EthoState.exe"; Description: "Launch EthoState"; Flags: nowait postinstall skipifsilent

