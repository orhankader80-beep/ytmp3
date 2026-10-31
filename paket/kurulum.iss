; YouTube MP3 - Windows kurulum programı (Inno Setup 6)
; Derleme: ISCC.exe /DSurum=3.4 paket\kurulum.iss
#ifndef Surum
  #define Surum "0.0"
#endif

[Setup]
AppId={{8C1F2E7A-5B3D-4C9E-9A71-3F2D6B8E4A10}
AppName=YouTube MP3
AppVersion={#Surum}
AppVerName=YouTube MP3 {#Surum}
AppPublisher=orhankader80-beep
AppPublisherURL=https://github.com/orhankader80-beep/ytmp3
DefaultDirName={localappdata}\Programs\YouTube MP3
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=..\cikti
OutputBaseFilename=YouTubeMP3-Kurulum
SetupIconFile=ikon.ico
UninstallDisplayIcon={app}\YouTube MP3.exe
UninstallDisplayName=YouTube MP3
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Languages]
Name: "tr"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "masaustu"; Description: "Masaüstüne kısayol oluştur"

[Files]
Source: "..\dist\YouTube MP3\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\YouTube MP3"; Filename: "{app}\YouTube MP3.exe"
Name: "{autodesktop}\YouTube MP3"; Filename: "{app}\YouTube MP3.exe"; Tasks: masaustu

[Run]
Filename: "{app}\YouTube MP3.exe"; Description: "YouTube MP3'ü başlat"; Flags: nowait postinstall
