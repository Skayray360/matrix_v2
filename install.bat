@echo off
REM Creado por Aldo Garcia. Entrada portable; conserva el instalador existente.
call "%~dp0INSTALAR_MATRIX_RH.bat" %*
exit /b %ERRORLEVEL%
