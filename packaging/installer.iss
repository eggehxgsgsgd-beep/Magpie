; Inno Setup script for Magpie
; Expects /DAppVersion, /DSourceDir, /DOutputDir from the command line.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\Magpie"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif

[Setup]
AppName=Magpie
AppVersion={#AppVersion}
AppPublisher=mangoa
DefaultDirName={autopf}\Magpie
DefaultGroupName=Magpie
UninstallDisplayIcon={app}\Magpie.exe
OutputBaseFilename=Magpie-{#AppVersion}-windows-x64-setup
OutputDir={#OutputDir}
Compression=lzma2
SolidCompression=yes
SetupIconFile=app.ico
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Magpie"; Filename: "{app}\Magpie.exe"
Name: "{autodesktop}\Magpie"; Filename: "{app}\Magpie.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{app}\Magpie.exe"; Description: "Launch Magpie"; Flags: nowait postinstall skipifsilent
