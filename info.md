[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]


Cette intégration permet de piloter les poêles à granulés Ravelli Circular depuis Home Assistant.

Testée avec le poêle Ravelli Circular 8 (elle devrait fonctionner avec d'autres poêles équipés d'un module wifi Winet Control).

**Plateformes créées :**

Plateforme | Description
-- | --
`binary_sensor` | Indicateurs à vrai ou faux (par exemple l'état d'alarme).
`sensor` | Mesures et états du poêle.
`switch` | Commandes marche/arrêt et modes de régulation.
`number` | Réglage de la puissance et du delta éco.
`climate` | Contrôle en mode thermostat.

![logo][logoimg]

{% if not installed %}
## Installation

1. Cliquer sur installer.
2. Redémarrer Home Assistant.
3. Dans l'interface, aller dans « Paramètres » → « Appareils et services », cliquer sur « + Ajouter une intégration » et chercher « Ravelli ».

{% endif %}


## Configuration

La configuration se fait dans l'interface Home Assistant, avec l'adresse IP du module Winet du poêle.

***

[releases-shield]: https://img.shields.io/github/v/release/GUILEB/integration_circular
[releases]: https://github.com/GUILEB/integration_circular/releases
[commits-shield]: https://img.shields.io/github/check-runs/GUILEB/integration_circular/fe39dd96b270fd23de742a0112f131b8058ec259
[commits]: https://github.com/GUILEB/integration_circular/commits/master
[license-shield]: https://img.shields.io/github/license/GUILEB/integration_circular
[license]: https://github.com/GUILEB/integration_circular/blob/master/LICENSE
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-GUILEB-blue.svg?style=for-the-badge
[user_profile]: https://github.com/GUILEB/
[buymecoffee]: https://buymeacoffee.com/guillaumelk
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[logoimg]: logo.png
