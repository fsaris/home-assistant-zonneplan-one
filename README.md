# Zonneplan | Energie integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://hacs.xyz/)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg?style=for-the-badge&color=green)

Unofficial integration for Zonneplan | Energie

## Current features
- Zonneplan:
   - Solar panels: _(available when you have 1 or more Zonneplan solar inverters)_
     - Yield today: `kWh` (combined yield of all Zonneplan solar inverters) _(can be used as entity on Energy Dashboard)_
   - General energy values: _(available when there is a P1 reader from Zonneplan)_
     - Electricity consumed today: `kWh` _(can be used as entity on Energy Dashboard)_
     - Electricity returned today: `kWh` _(can be used as entity on Energy Dashboard)_
     - Gas consumption today: `m³`
     - Electricity today low tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
     - Electricity today normal tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
     - Electricity today high tariff: `kWh` _(can be used as entity on Energy Dashboard, default disabled)_
 - Energy contract related sensors: _(available when you have a Zonneplan energy contract)_
     - Current Zonneplan Electricity tariff: `€/kWh`
       - The full Electricity forecast is available as a forecast attribute of this sensor
     - Current Zonneplan Gas tariff: `€/m³`
     - Next Zonneplan Gas tariff: `€/m³` 
     - 8 hours forecast of Zonneplan Electricity tariff: `€/kWh` _(default disabled, available when you have a energy contract)_
     - Current electricity usage
     - Sustainability score
     - Electricity delivery costs today
     - Electricity production costs today
     - Gas delivery costs today
- Zonneplan Solar inverter sensors: _(available when you have a Zonneplan solar inverter)_
   - Yield total: `kWh`
   - First measured: `date` _(default disabled)_
   - Last measured value: `W`
   - Last measured: `date`
   - Powerplay enabled: `on/off` _(default disabled)_
   - Powerplay/power limit active: `on/off` _(default disabled)_
   - Powerplay total: `€` _(default disabled)_
   - Powerplay today: `€` _(default disabled)_
   - Current scenario _(default disabled)_
- Zonneplan Connect (P1 reader) sensors: _(available when there is a P1 reader from Zonneplan)_
   - Electricity consumption: `W`
   - Electricity production: `W`
   - Electricity average: `W` (average use over the last 5min)
   - Electricity first measured: `date` _(default disabled)_
   - Electricity last measured: `date`
   - Electricity last measured production: `date`
   - Gas first measured: `date` _(default disabled)_
   - Gas last measured: `date`
- Charge point/Laadpaal: _(available when charge point contract)_
  - Charge point state
  - Charge point power `W`
  - Charge point energy delivered session `kWh`
  - Charge point next schedule start `date`
  - Charge point next schedule end `date`
  - Charge point dynamic load balancing health _(default disabled)_
  - Charge point connectivity state `on/off`
  - Charge point can charge `on/off`
  - Charge point can schedule `on/off`
  - Charge point charging manually `on/off`
  - Charge point charging automatically `on/off`
  - Charge point plug and charge `on/off`
  - Charge point overload protection active `on/off` _(default disabled)_
  - Buttons to start/stop charge
- Battery: _(available when there is a Zonneplan Thuisbatterij)_
  - Battery state
  - Percentage `%`
  - Power `W` _(default disabled)_
  - Delivery today `kWh`
  - Production today `kWh`
  - Today `€`
  - Total `€`
  - Dynamic charging enabled `on/off`
  - Dynamic load balancing overload active `on/off`
  - Dynamic load balancing overload enabled `on/off`
  - Manual control enabled `on/off`
  - Inverter state _(default disabled)_
  - Manual control state _(default disabled)_
  - First measured `datetime` _(default disabled)_
  - Last measured `datetime`

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
1. In Home Assistant click on `Configuration` -> `Integrations` -> `+ Add integration` and search for and select `Zonneplan ONE` [![Open your Home Assistant instance and start setting up Zonneplan.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zonneplan_one)
1. Enter you `emailaddress` you also use in the **Zonneplan ONE** app
1. You will get an email to verify the login.
1. Click "Save"
1. Enjoy

## Setup Energy Dashboard

#### Solar production
`Zonneplan Yield total` is what your panels produced

#### Grid consumption  
`Zonneplan Electricity consumption today` is what you used from the grid

#### Return to grid
`Zonneplan Electricity returned today` is what you returned to the grid

### Installing main/beta version using HACS
1. Go to `HACS` => `Integrations`
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
