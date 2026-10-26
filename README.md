# Ravelli Circular Integration
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![GitHub Issues][issues-shield]][issues]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield] [![hacs][hacsbadge]][hacs]

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

Cette intégration permet de piloter les poêles à granulés **Ravelli Circular** depuis Home Assistant, en local, via le module wifi **Winet Control** du poêle.

Testée avec le poêle Ravelli Circular 8. Elle devrait fonctionner avec d'autres poêles équipés d'un module Winet Control, mais ce n'est pas vérifié.

**Plateformes créées :**

Plateforme | Description
-- | --
`binary_sensor` | Indicateurs à vrai ou faux (par exemple l'état d'alarme).
`sensor` | Mesures et états du poêle (températures, statut).
`switch` | Marche/arrêt du poêle et modes de régulation (régulation par sonde externe, mode éco).
`number` | Réglage de la puissance et du delta du mode éco.
`climate` | Contrôle en mode thermostat.

![logo][logoimg]

## Prérequis

- Home Assistant 2024.9.0 ou plus récent.
- Le poêle doit être joignable en réseau local depuis Home Assistant. Il faut connaître son adresse IP.

## Installation par HACS

1. Dans HACS, ouvrir le menu « ⋮ » puis « Dépôts personnalisés ».
2. Ajouter `https://github.com/GUILEB/integration_circular` avec la catégorie **Intégration**.
3. Installer « Ravelli Circular » depuis HACS, puis redémarrer Home Assistant.

## Installation manuelle

1. Ouvrir le dossier de configuration de Home Assistant (celui qui contient `configuration.yaml`).
2. Créer le dossier `custom_components` s'il n'existe pas.
3. Dans `custom_components`, créer un dossier nommé **`circular`**. Le nom doit être exactement `circular`, car c'est le domaine de l'intégration.
4. Copier **tous** les fichiers du dossier `custom_components/circular/` de ce dépôt dans ce nouveau dossier.
5. Redémarrer Home Assistant.

Le dossier doit ressembler à ceci :

```text
custom_components/circular/__init__.py
custom_components/circular/api.py
custom_components/circular/binary_sensor.py
custom_components/circular/climate.py
custom_components/circular/config_flow.py
custom_components/circular/const.py
custom_components/circular/coordinator.py
custom_components/circular/entity.py
custom_components/circular/manifest.json
custom_components/circular/number.py
custom_components/circular/sensor.py
custom_components/circular/switch.py
custom_components/circular/translations/en.json
custom_components/circular/translations/fr.json
custom_components/circular/winet/
```

## Configuration

La configuration se fait dans l'interface Home Assistant :

1. Aller dans « Paramètres » → « Appareils et services ».
2. Cliquer sur « + Ajouter une intégration » et chercher **Ravelli**.
3. Renseigner l'adresse IP du module Winet du poêle.
4. Optionnel : choisir un capteur de température. Sa valeur est alors envoyée au poêle en régulation par sonde externe.

## Registres utilisés

L'intégration communique avec le module Winet par HTTP local. Les registres connus sont décrits dans `custom_components/circular/winet/const.py`.

Registre | Rôle
-- | --
2 | Statut du poêle
3 | Alarmes
6 | Température de la sonde
50 | Consigne de température
51 | Puissance
187 | Vitesse du ventilateur d'air ambiant

Les autres registres sont encore inconnus. Certains sont lus sans être décodés.

## Limites connues

- Pas d'authentification : l'intégration parle au module Winet en HTTP sur le réseau local.
- Un seul poêle par entrée de configuration. Deux poêles du même modèle ne peuvent pas être ajoutés, car l'identifiant unique est basé sur le modèle.
- Le capteur `error_offline` indique un état d'alarme du poêle. Ce n'est pas une mesure de la connexion au module.

## Contribuer

Les contributions sont bienvenues. Lire d'abord le [guide de contribution](CONTRIBUTING.md).

***
[logoimg]: logo.png

[releases-shield]: https://img.shields.io/github/v/release/GUILEB/integration_circular

[releases]: https://github.com/GUILEB/integration_circular/releases

[issues-shield]: https://img.shields.io/github/issues/GUILEB/integration_circular

[issues]: https://github.com/GUILEB/integration_circular/issues

[commits-shield]: https://img.shields.io/github/check-runs/GUILEB/integration_circular/fe39dd96b270fd23de742a0112f131b8058ec259

[commits]: https://github.com/GUILEB/integration_circular/commits/master

[license-shield]: https://img.shields.io/github/license/GUILEB/integration_circular

[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge

[maintenance-shield]: https://img.shields.io/badge/maintainer-GUILEB-blue.svg?style=for-the-badge

[buymecoffee]: https://buymeacoffee.com/guillaumelk
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
