# Ravelli Circular Integration
[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![GitHub Issues][issues-shield]][issues]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield] [![hacs][hacsbadge]][hacs]

[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

This component enable the control of Ravelli Circular Pellet Stoves by Home Assistant.

Tested with the Ravelli Circular 8 pellet stove (not tested on others stoves but should work if the stove uses a Winet Control wifi module)

_Integration to integrate with [integration_blueprint][integration_blueprint] and [integration_invicta][integration_invicta]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.
`sensor` | Show info from blueprint API.
`switch` | Switch something `True` or `False`.

![logo][logoimg]

## Installation by HACS

TODO

## Installation (Manual)

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `integration_circular`.
4. Download _all_ the files from the `custom_components/integration_circular/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant
7. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration circular"

Using your HA configuration directory (folder) as a starting point you should now also have this:

```text
custom_components/integration_circular/translations/en.json
custom_components/integration_circular/translations/nb.json
custom_components/integration_circulartranslations/sensor.nb.json
custom_components/integration_circular/__init__.py
custom_components/integration_circular/api.py
custom_components/integration_circular/binary_sensor.py
custom_components/integration_circular/config_flow.py
custom_components/integration_circular/const.py
custom_components/integration_circular/manifest.json
custom_components/integration_circular/sensor.py
custom_components/integration_circular/switch.py
```

## Configuration is done in the UI

<!---->

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***
[logoimg]: logo.png

[integration_blueprint]: https://github.com/ludeeus/integration_blueprint
[integration_invicta]: https://github.com/docteurzoidberg/ha-invicta

[releases-shield]: https://img.shields.io/github/v/release/GUILEB/integration_circular

[releases]: (https://github.com/GUILEB/integration_circular/releases)

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


