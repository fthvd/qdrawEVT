@echo off
set Letter=K:
if exist "%Letter%\" (subst "%Letter%" /D)>nul
if %errorlevel%==0 echo Lecteur %Letter% demonte
if %errorlevel%==1 echo Le lecteur %Letter% est affecte au reseau ou a deja ete demonte
set Letter=R:
if exist "%Letter%\" (subst "%Letter%" /D)>nul
if %errorlevel%==0 echo Lecteur %Letter% demonte
if %errorlevel%==1 echo Le lecteur %Letter% est affecte au reseau ou a deja ete demonte
set Letter=S:
if exist "%Letter%\" subst "%Letter%" /D>nul
if %errorlevel%==0 echo Lecteur %Letter% demonte
if %errorlevel%==1 echo Le lecteur %Letter% est affecte au reseau ou a deja ete demonte
set Letter=T:
if exist "%Letter%\" subst "%Letter%" /D>nul
if %errorlevel%==0 echo Lecteur %Letter% demonte
if %errorlevel%==1 echo Le lecteur %Letter% est affecte au reseau ou a deja ete demonte
set Letter=W:
if exist "%Letter%\" subst "%Letter%" /D>nul
if %errorlevel%==0 echo Lecteur %Letter% demonte
if %errorlevel%==1 echo Le lecteur %Letter% est affecte au reseau ou a deja ete demonte
echo Demontage termine
pause


