@echo off
REM ------------------------------------------------------
REM Freebox Dashboard - Script de lancement Windows amélioré
REM ------------------------------------------------------
SETLOCAL ENABLEDELAYEDEXPANSION

REM 1️⃣ Définir le port par défaut
SET PORT=5000

REM 2️⃣ Vérifier si le port est utilisé
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :!PORT! ^| findstr LISTENING') do (
    echo Port !PORT! déjà utilisé par PID %%a
    SET /P USERPORT=Choisir un autre port ou ENTER pour passer à !PORT! par défaut :
    if not "!USERPORT!"=="" SET PORT=!USERPORT!
)
echo Port utilisé pour Flask: !PORT!

echo Positionnement dans le dossier "C:\Users\fdaub\Documents\Github\Freebox-API"
cd "C:\Users\fdaub\Documents\Github\Freebox-API"

REM 3️⃣ Créer l'environnement virtuel si absent
IF NOT EXIST ".venv\Scripts\activate" (
    echo Création de l'environnement virtuel...
    python -m venv .venv
)

REM 4️⃣ Activer l'environnement virtuel
echo Activation de l'environnement virtuel...
call .venv\Scripts\activate

REM 5️⃣ Mise à jour de pip
echo Mise a jour de pip...
python -m pip install --upgrade pip

REM 6️⃣ Installer les dépendances
IF EXIST "requirements.txt" (
    echo Installation des dépendances...
    pip install -r requirements.txt
) ELSE (
    echo ATTENTION: requirements.txt introuvable!
)

REM 7️⃣ Lancer l'application Flask avec relance automatique
:RESTART
echo Lancement de freebox_dashboard_app.py sur le port !PORT!...
python freebox_dashboard_app.py
IF ERRORLEVEL 1 (
    echo L'application a planté. Redemarrage dans 5 secondes...
    timeout /t 5
    goto RESTART
)

pause
