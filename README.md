# Zonneplan ONE component for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://hacs.xyz/)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg?style=for-the-badge&color=green)

Unofficial integration for Zonneplan ONE solar inverter + Zonneplan connect

## Current features
- Support for Solar inverter + P1 device
- Solar inverter sensors:
   - Highest yield _(default disabled)_
   - Highest yield _(default disabled)_
   - Yield total
   - Yield today  
   - First measured _(default disabled)_
   - Last measured value
   - Last measured   
- P1 device sensors: (when available)
   - Electricity today
   - Electricity consumption
   - Electricity production
   - Electricity average (average use over the last 5min)
   - Electricity first measured _(default disabled)_
   - Electricity last measured
   - Electricity last measured production
   - Gas consumption today
   - Gas last measured consumption
   - Gas first measured _(default disabled)_
   - Gas last measured

## Installation

### Install with HACS (recommended)

Do you have [HACS](https://hacs.xyz/) installed?
1. Search integrations for **Zonneplan ONE**
1. Click `Install`
1. Restart Home Assistant
1. See [Setup](#setup)

### Install manually

1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
2. Create another folder `zonneplan_one` in the `custom_components` folder. Copy all files from `custom_components/zonneplan_one` into the `zonneplan_one` folder.

## Setup
1. In Home Assitant click on `Configuration`
1. Click on `Integrations`
1. Click on `+ Add integration`
1. Search for and select `Zonneplan ONE`
1. Enter you `emailaddress` you also use in the **Zonneplan ONE** app
1. You will get an email to verify the login.
1. Click "Save"
1. Enjoy


### Installing main/beta version using HACS
1. Go to `HACS` => `Integratrions`
1. Click on the three dots icon in right bottom of the **Zonneplan ONE** card
1. Click `Reinstall`
1. Make sure `Show beta versions` is checked
1. Select version `main`
1. Click install and restart HA

### Troubleshooting

If you run into issues during setup or when entries do not update anymore please increase logging and provide them when creating an issue:

Add `custom_components.zonneplan_one: debug` to the logger config in you `configuration.yaml`:

```
logger:
  logs:
    custom_components.zonneplan_one: debug
```
