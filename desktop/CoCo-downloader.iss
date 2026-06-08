; Inno Setup installer script for CoCo Downloader.

#define MyAppName "CoCo Downloader"
#define MyAppExeName "CoCo-downloader.exe"
#define MyAppPublisher "markcxx"
#define MyAppURL "https://github.com/markcxx/coco-downloader"
#define EnvAppVersion GetEnv("APP_VERSION")
#if EnvAppVersion == ""
  #define MyAppVersion "0.0.1"
#else
  #define MyAppVersion EnvAppVersion
#endif

[Setup]
AppId={{9DA8A01E-E207-4ED9-B3A3-07C55DD04071}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\CoCo Downloader
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=CoCo-downloader-v{#MyAppVersion}-Windows-x86_64-Setup
SetupIconFile=app/resource/images/logo/CocoDownloader.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "build\CoCo-downloader.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
