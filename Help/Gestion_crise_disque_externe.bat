@echo off
chcp 65001>nul
set Letter=K:
net use | find "%Letter%"
if %errorlevel%==1 goto :suite
net use "%Letter%" /delete /yes
:suite
if exist "%Letter%\" (subst "%Letter%" /D)>nul
set Letter=R:
net use | find "%Letter%"
if %errorlevel%==1 goto :suite
net use "%Letter%" /delete /yes
:suite
if exist "%Letter%\" (subst "%Letter%" /D)>nul
set Letter=S:
net use | find "%Letter%"
if %errorlevel%==1 goto :suite
net use "%Letter%" /delete /yes
:suite
if exist "%Letter%\" subst "%Letter%" /D>nul
set Letter=T:
net use | find "%Letter%"
if %errorlevel%==1 goto :suite
net use "%Letter%" /delete /yes
:suite
if exist "%Letter%\" subst "%Letter%" /D>nul
set Letter=W:
net use | find "%Letter%"
if %errorlevel%==1 goto :suite
net use "%Letter%" /delete /yes
:suite
if exist "%Letter%\" subst "%Letter%" /D>nul
wmic logicaldisk get volumename,name > C:\users\%USERNAME%\Documents\nom_lettrevolume.txt
set nom_lettre=C:\users\%USERNAME%\Documents\nom_lettrevolume.txt
for /f "skip=1 tokens=1,2" %%a in ('type "%nom_lettre%"') do (
	if CRISE_HDD == %%b (subst K: %%a\dossiers)
	if CRISE_HDD == %%b (subst R: %%a\gb_ref)
	if CRISE_HDD == %%b (subst S: %%a\gb_prod)
	if CRISE_HDD == %%b (subst T: %%a\gb_cons)
	if CRISE_HDD == %%b (subst W: %%a\fichiers_sig)
	if CRISE_HDD == %%b (set lp=CRISE_HDD)
)
exit
