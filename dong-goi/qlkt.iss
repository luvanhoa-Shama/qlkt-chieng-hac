; Bộ cài Windows (Inno Setup 6). Dựng: iscc /DPhienBan=1.0.0 dong-goi\qlkt.iss
; Cài theo người dùng (không cần quyền quản trị máy); cho phép chọn cài cho mọi người nếu có quyền.
; Gỡ cài đặt KHÔNG xóa dữ liệu (%LOCALAPPDATA%\QLKT-ChiengHac): dữ liệu và bản sao lưu được giữ lại.

#ifndef PhienBan
  #define PhienBan "0.0.0"
#endif

[Setup]
AppId={{6B1F3C2E-8D4A-4E7B-9C21-5A0F7D3E9B14}
AppName=QLKT Chieng Hac
AppVerName=QLKT Chieng Hac {#PhienBan}
AppVersion={#PhienBan}
AppPublisher=UBND xa Chieng Hac
DefaultDirName={autopf}\QLKT Chieng Hac
DefaultGroupName=QLKT Chieng Hac
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=QLKT-ChiengHac-CaiDat-{#PhienBan}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
UninstallDisplayIcon={app}\QLKT.exe

[Tasks]
Name: "desktopicon"; Description: "Tao bieu tuong tren man hinh (Desktop)"; Flags: checkedonce

[Files]
Source: "..\dist\QLKT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Quan ly thi dua - khen thuong"; Filename: "{app}\QLKT.exe"
Name: "{autodesktop}\QLKT Chieng Hac"; Filename: "{app}\QLKT.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\QLKT.exe"; Description: "Mo phan mem"; Flags: nowait postinstall skipifsilent
