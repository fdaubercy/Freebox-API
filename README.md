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

## Licence

Ce projet est sous licence MIT.