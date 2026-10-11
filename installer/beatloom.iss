; Instalador do Beatloom (Inno Setup 6). So embrulha o start.bat: copia o repositorio e cria os atalhos.
; Python, torch e padroes nao vao aqui dentro; quem baixa e o start.bat e a tela de preparo.
; Quem monta e a CI (.github\workflows\release.yml) ao subir uma tag v*. A mao: ISCC.exe installer\beatloom.iss -> .cache\beatloom-setup.exe
#ifndef Versao
  #define Versao "1.0.0"
#endif

[Setup]
AppId={{7B1E0C52-6C0B-4E5E-9C1F-BEA7100B5A4D}
AppName=Beatloom
AppVersion={#Versao}
AppPublisherURL=https://github.com/bps2414/beatloom
; pasta gravavel sem administrador: o app baixa coisas para dentro dela
DefaultDirName={localappdata}\Beatloom
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableDirPage=yes
LicenseFile=..\LICENSE
SetupIconFile=beatloom.ico
UninstallDisplayIcon={app}\installer\beatloom.ico
OutputDir=..\.cache
OutputBaseFilename=beatloom-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[CustomMessages]
en.Abrir=Open Beatloom now (the first time it downloads about 2 GB)
pt.Abrir=Abrir o Beatloom agora (na primeira vez ele baixa uns 2 GB)
en.ManterMapas=Keep the maps you generated (the saida folder)?
pt.ManterMapas=Manter os mapas que você gerou (a pasta saida)?

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"

[Files]
; lista explicita: dados, saida, musicas, bin e beatloom.json nunca entram
Source: "..\start.bat"; DestDir: "{app}"
Source: "..\start-bandeja.bat"; DestDir: "{app}"
Source: "..\*.py"; DestDir: "{app}"; Excludes: "test_*.py"
Source: "..\requirements.txt"; DestDir: "{app}"
Source: "..\LICENSE"; DestDir: "{app}"
Source: "..\README*.md"; DestDir: "{app}"
Source: "..\beatloom\*.py"; DestDir: "{app}\beatloom"
Source: "..\tools\*.py"; DestDir: "{app}\tools"
Source: "..\tools\bandeja.ps1"; DestDir: "{app}\tools"
Source: "..\site\*"; DestDir: "{app}\site"; Flags: recursesubdirs
Source: "..\check\check.mjs"; DestDir: "{app}\check"
Source: "..\check\package*.json"; DestDir: "{app}\check"
Source: "..\docs\ARCHITECTURE*.md"; DestDir: "{app}\docs"
Source: "beatloom.ico"; DestDir: "{app}\installer"

[Icons]
Name: "{autoprograms}\Beatloom"; Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\beatloom.ico"
Name: "{autoprograms}\Beatloom (bandeja)"; Filename: "{app}\start-bandeja.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\beatloom.ico"
Name: "{autodesktop}\Beatloom"; Filename: "{app}\start.bat"; WorkingDir: "{app}"; IconFilename: "{app}\installer\beatloom.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\start.bat"; Description: "{cm:Abrir}"; Flags: postinstall nowait skipifsilent

[Code]
// o desinstalador so conhece o que ele copiou; o que o app baixou (.venv, bin, dados...) sai aqui, e os mapas so se a pessoa deixar
procedure Apaga(Nome: String);
begin
  DelTree(ExpandConstant('{app}\') + Nome, True, True, True);
end;

procedure CurUninstallStepChanged(Passo: TUninstallStep);
begin
  if Passo <> usPostUninstall then Exit;
  if DirExists(ExpandConstant('{app}\saida')) and (MsgBox(CustomMessage('ManterMapas'), mbConfirmation, MB_YESNO) = IDYES) then begin
    Apaga('.venv'); Apaga('.cache'); Apaga('bin'); Apaga('dados'); Apaga('arcviewer'); Apaga('musicas'); Apaga('__pycache__');
    Apaga('beatloom'); Apaga('tools'); Apaga('site'); Apaga('check'); Apaga('docs'); Apaga('installer');
    DeleteFile(ExpandConstant('{app}\beatloom.json'));
    DeleteFile(ExpandConstant('{app}\dados_download.log'));
  end else
    DelTree(ExpandConstant('{app}'), True, True, True);
end;
