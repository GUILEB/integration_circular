[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]][license]

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]


This component enable the control of Ravlleli Pellet Stoves by Home Assistant.

Tested with the Ravlleli Circular 8 pellet stove (not tested on others stoves but should work if the stove uses a Winet Control wifi module)

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info from API.
`switch` | Switch something `True` or `False`.

![logo][logoimg]

{% if not installed %}
## Installation

1. Click install.
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Blueprint".

{% endif %}


## Configuration is done in the UI

<!---->

***

[integration_circular]: https://github.com/GUILEB/integration_circular
[buymecoffee]: https://www.buymeacoffee.com/drzoid
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
<!-- [commits-shield]: https://img.shields.io/github/commit-activity/y/docteurzoidberg/ha-invicta.svg?style=for-the-badge -->
[commits]: https://github.com/GUILEB/integration_circular/commits/master
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[logoimg]: logo_invicta.png
[license]: https://github.com/GUILEB/integration_circular/blob/master/LICENSE
<!-- [license-shield]: https://img.shields.io/github/license/docteurzoidberg/ha-invicta.svg?style=for-the-badge -->
<!-- [maintenance-shield]: https://img.shields.io/badge/maintainer-DrZoid-blue.svg?style=for-the-badge -->
<!--[releases-shield]: https://img.shields.io/github/release/docteurzoidberg/ha-invicta.svg?style=for-the-badge -->
[releases]: https://github.com/GUILEB/integration_circular/releases
[user_profile]: https://github.com/GUILEB/