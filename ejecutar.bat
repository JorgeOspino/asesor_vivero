@echo off
:: Cambia esta ruta por la ubicación exacta de la carpeta de tu proyecto
cd /d "C:\Users\HP\OneDrive\Desktop\asesor_vivero"

:: Activa el entorno virtual
call .venv\Scripts\activate

:: Ejecuta el orquestador principal
python main_diario.py