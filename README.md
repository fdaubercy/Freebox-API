# Freebox-API

## Description

Ce projet est une API Python pour interagir avec les services Freebox. Il permet d'autoriser l'accès à la Freebox, de récupérer des informations et de gérer un tableau de bord simple via une interface web.

## Fonctionnalités

- Autorisation automatique avec la Freebox
- Récupération d'informations système
- Interface web pour le tableau de bord
- Gestion des catégories et des données

## Installation

1. Clonez le dépôt :
   ```
   git clone https://github.com/fdaubercy/Freebox-API.git
   cd Freebox-API
   ```

2. Installez les dépendances :
   ```
   pip install -r requirements.txt
   ```

## Utilisation

### Autorisation
Exécutez le script d'autorisation pour obtenir un token d'accès :
```
python freebox_authorize.py
```

### Tableau de bord
Lancez l'application web :
```
python freebox_dashboard_app.py
```
Puis ouvrez votre navigateur à l'adresse `http://localhost:5000`.

## Tests

Pour exécuter les tests :
```
python -m pytest tests/
```

## Structure du projet

- `freebox_authorize.py` : Script d'autorisation
- `freebox_dashboard_app.py` : Application Flask pour le tableau de bord
- `templates/` : Templates HTML pour l'interface web
- `static/` : Fichiers statiques (CSS, JS)
- `tests/` : Tests unitaires

## Configuration

Modifiez `config.json` pour ajuster les paramètres de configuration.

## Versions du script
✅ v1.1.2
- Graphiques temps réel : débit, Wi-Fi, DHCP
- Historique 24h / 7j à partir des fichiers JSON
- Endpoint /metrics compatible Prometheus
- Possibilité HTTPS via Flask ou reverse proxy Nginx
- Intégration complète avec alertes et cooldown existants

- Ajout d'un script: 'run_freebox.bat':
    * Active l’environnement virtuel .venv
    * Installe les dépendances si elles ne sont pas déjà installées
    * Lance freebox_dashboard_app.py avec WebSocket

✅ v1.1.1
- Alertes débit & WiFi configurables
- Anti-spam automatique
- Graphiques temps réel evolue toutes les 30s
- Prêt pour Grafana / Prometheus
- Fonctionne en mode headless
- Boutons fonctionnels
- Alertes partir si seuil dépassé
- Reconnexion Freebox automatique
- Backoff intelligent
- Graphique clients Wi-Fi temps réel
- Alertes Wi-Fi down
- Toujours compatible headless

✅ v1.1.0
- Scheduler APScheduler pour requêtes régulières sur Freebox
- WebSocket pour mise à jour temps réel du dashboard
- Stockage des données JSON pour graphiques historiques
- Alertes automatiques par mail et Discord
- Dashboard Flask avec pages HTML externes et icônes sur les boutons
- Activer / désactiver les alertes sans modifier le code
- Mail et Discord indépendants
- TLS, login SMTP supportés
- Prêt pour alertes intelligentes (seuils, uptime, etc.)

✅ v1.0
- Le scheduler APScheduler poll l’API Freebox toutes les 30s/5min
- Les réponses sont stockées dans des fichiers JSON (data_status.json, data_wifi,json, data_dhcp.json)
- Les pages HTML sont externes, modifiables à chaud
- Dashboard et catégories fonctionnent avec icônes et tableaux centrés


✅ Points forts
- APScheduler exécute les tâches en arrière-plan.
- Pas besoin de boucle while True pour chaque tâche, la planification est intégrée.
- Compatible Flask : tu peux lancer start_scheduler() dans freebox_dashboard_app.py pour avoir les polls en parallèle avec ton dashboard.
- Facile à étendre : tu peux ajouter des tâches pour /downloads, /calls, /storage etc.
- Page web dédiée au paramétrage
- Accessible depuis le dashboard via un bouton type menu
- Permet de modifier :
    Activation/désactivation des alertes
    Cooldown alertes
    Seuils débit minimum et Wi-Fi
    Modifications persistées dans config.json
- Protégé par JWT / login
- Simple à étendre pour d’autres paramètres si besoin

## Licence

Ce projet est sous licence MIT.