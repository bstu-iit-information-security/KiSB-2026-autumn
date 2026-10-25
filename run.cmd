@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "labRoot=%~dp0"
for %%I in ("%labRoot%..\KiSB-extra\build") do set "labBuild=%%~fI"
if not exist "%labBuild%" mkdir "%labBuild%"
if errorlevel 1 exit /b 1
where cl >nul 2>nul
if errorlevel 1 call "D:\CodexTools\VisualStudioBuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /O2 /W4 /MT /utf-8 /D_CRT_SECURE_NO_WARNINGS "%labRoot%lab1\src\tsevan\main.cpp" /Fo"%labBuild%\lab1.obj" /Fe"%labBuild%\lab1.exe"
if errorlevel 1 exit /b 1
pushd "%labRoot%lab1\src\tsevan"
"%labBuild%\lab1.exe"
set "labResult=%errorlevel%"
popd
if not "%labResult%"=="0" exit /b %labResult%
exit /b 0
