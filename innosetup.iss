[Setup]
AppName=JRule for Mplus
AppVerName=Jrule for Mplus beta 1
AppPublisher=Daniel Oberski
AppPublisherURL=http://www.daob.org/
DefaultDirName={pf}\JruleMplus
DefaultGroupName=JRuleMplus
DisableProgramGroupPage=true
OutputBaseFilename=JRuleMplusSetup
Compression=lzma
SolidCompression=true
AllowUNCPath=false
VersionInfoVersion=0.9
VersionInfoCompany=daniel oberski daob
VersionInfoDescription=JRuleMplus
LicenseFile = license.txt

[Dirs]
Name: {app}; Flags: uninsalwaysuninstall;

[Files]
Source: dist\*; DestDir: {app}; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: {group}\JRuleMplus; Filename: {app}\JRuleMplus.exe; WorkingDir: {app}

[Run]
Filename: {app}\JRuleMplus.exe; Description: {cm:LaunchProgram,JRuleMplus}; Flags: nowait postinstall skipifsilent

