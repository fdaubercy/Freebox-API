# Script d'autorisation automatique Freebox OS (API v15.0) avec barre de progression, pourcentage et notification sonore
# A lancer UNE SEULE FOIS pour obtenir app_token

import requests
import time
import json
import sys
import os

FREEBOX_URL = "http://mafreebox.freebox.fr"
API_VERSION = "v15"
API_BASE = f"{FREEBOX_URL}/api/{API_VERSION}"

APP_ID = "fr.freebox.webapp"
APP_NAME = "Freebox Web App"
APP_VERSION = "1.0"
DEVICE_NAME = "Python Web Server"

# Sauvegarde du token dans le même dossier que ce script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_TOKEN_FILE = os.path.join(SCRIPT_DIR, "app_token.json")


def authorize():
    payload = {
        "app_id": APP_ID,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "device_name": DEVICE_NAME
    }

    r = requests.post(f"{API_BASE}/login/authorize/", json=payload).json()

    if not r.get("success"):
        raise Exception(r)

    print("➡️  Valide l'autorisation sur l'écran de la Freebox Pop")
    return r["result"]


def wait_for_validation(track_id, max_wait=120):
    elapsed = 0
    bar_length = 30

    while True:
        r = requests.get(f"{API_BASE}/login/authorize/{track_id}").json()
        status = r["result"]["status"]

        # calcul du pourcentage de progression
        percent = min(elapsed / max_wait, 1.0)
        filled_length = int(bar_length * percent)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)

        remaining = max_wait - elapsed
        sys.stdout.write(f'[{bar}] {percent*100:.0f}% Statut: {status} | Temps écoulé: {elapsed}s | Temps restant estimé: {remaining}s\r')
        sys.stdout.flush()

        if status == "granted":
            print("\n✅ Autorisation accordée !")
            # Notification sonore simple (Windows et Linux)
            if os.name == 'nt':
                import winsound
                winsound.Beep(1000, 500)  # fréquence 1000Hz, durée 0.5s
            else:
                print('\a')  # son système sous Linux/Mac
            return True

        if status == "denied":
            raise Exception("Autorisation refusée sur la Freebox")

        if elapsed >= max_wait:
            print("\n⚠️  Temps maximum atteint. Veuillez vérifier la Freebox.")
            return False

        time.sleep(2)
        elapsed += 2


if __name__ == "__main__":
    result = authorize()

    # app_token est fourni dans la réponse initiale
    app_token = result["app_token"]

    success = wait_for_validation(result["track_id"])

    if success:
        with open(APP_TOKEN_FILE, "w") as f:
            json.dump({"app_token": app_token}, f, indent=2)
        print("🔐 app_token sauvegardé dans app_token.json")
