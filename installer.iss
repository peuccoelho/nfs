; Inno Setup Script - Rei das NFS
; Instalador profissional para Windows

#define MyAppName "Rei das NFS"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NFS Tools"
#define MyAppURL "https://nfse2.camacari.ba.gov.br"
#define MyAppExeName "Rei_das_NFS.exe"

[Setup]
AppId={{8A2F8C12-9B3E-4D5A-9F1C-0E3D2B4A6F78}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=rei-das-nfs-instalador-v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile=img\icone.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na &Area de Trabalho"; GroupDescription: "Atalhos:"; Flags: checkedonce

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion
Source: "requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Oferece para abrir o programa ao finalizar
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
; Remove o Chromium do Playwright ao desinstalar
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{localappdata}\ms-playwright"""; Flags: runhidden
