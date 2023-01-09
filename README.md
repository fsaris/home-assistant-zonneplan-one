# Zonneplan ONE integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://hacs.xyz/)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg?style=for-the-badge&color=green)

Unofficial integration for Zonneplan ONE solar inverter + Zonneplan connect

## Current features
- Support for Zonneplan ONE + Connect
- Zonneplan ONE (Solar inverter) sensors:
   - Yield total: `kWh` _(can be used as entity on Energy Dashboard)_
   - Yield today: `kWh` _(can be used as entity on Energy Dashboard)_
   - First measured: `date` _(default disabled)_
   - Last measured value: `W`
   - Last measured: `date`
- Zonneplan Connect (P1 reader) sensors: (when available)
   - Electricity consumed today: `kWh` _(can be used as entity on Energy Dashboard)_
   - Electricity returned today: `kWh` _(can be used as entity on Energy Dashboard)_
   - Electricity today low tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
   - Electricity today normal tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
   - Electricity today high tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
   - Electricity consumption: `W`
   - Electricity production: `W`
   - Electricity average: `W` (average use over the last 5min)
   - Electricity first measured: `date` _(default disabled)_
   - Electricity last measured: `date`
   - Electricity last measured production: `date`
   - Gas consumption today: `m³`
   - Gas first measured: `date` _(default disabled)_
   - Gas last measured: `date`
- Additional sensors:
   - Current Zonneplan Electricity tariff: `€/kWh` _(default disabled)_
     - The full Electricity forecast is available as a forecast attribute of this sensor
   - Current Zonneplan Gas tariff: `€/m³` _(default disabled)_
   - 8 hours forecast of Zonneplan Electricity tariff: `€/kWh` _(default disabled)_
   - Current elektricity usage
   - Sustainability score

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
1. In Home Assistant click on `Configuration`
1. Click on `Integrations`
1. Click on `+ Add integration`
1. Search for and select `Zonneplan ONE`
1. Enter you `emailaddress` you also use in the **Zonneplan ONE** app
1. You will get an email to verify the login.
1. Click "Save"
1. Enjoy

## Setup Energy Dashboard

#### Solar production
`Zonneplan yield total` is what your panels produced

#### Grid consumption  
`Zonneplan P1 electricity consumption today` is what you used from the grid

#### Return to grid
`Zonneplan P1 electricity returned today` is what you returned to the grid

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
