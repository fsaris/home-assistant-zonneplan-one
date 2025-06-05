# Zonneplan integration for Home Assistant

![GitHub Release](https://img.shields.io/github/v/release/fsaris/home-assistant-zonneplan-one?style=for-the-badge)
![Active installations](https://badge.t-haber.de/badge/zonneplan_one?kill_cache=1)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://hacs.xyz/)
![stability-stable](https://img.shields.io/badge/stability-stable-green.svg?style=for-the-badge&color=green)
![GitHub License](https://img.shields.io/github/license/fsaris/home-assistant-zonneplan-one?style=for-the-badge)

Unofficial integration for Zonneplan. This integration uses the official Zonneplan API to pull the same data available in the Zonneplan app into your Home Assistant instance.

## Available sensors
### Zonneplan:
   - Solar panels: _(available when you have 1 or more Zonneplan solar inverters)_
     - Yield today: `kWh` (combined yield of all Zonneplan solar inverters) _(can be used as entity on Energy Dashboard)_
   - General energy values: _(available when there is a Zonneplan Connect P1 reader)_
     - Electricity consumed today: `kWh` _(can be used as entity on Energy Dashboard)_
     - Electricity returned today: `kWh` _(can be used as entity on Energy Dashboard)_
     - Gas consumption today: `m³`

### Zonneplan Connect (P1 reader):
<details>
<summary>Sensors available if you have a Zonneplan Connect P1 reader</summary>

   - Dsmr version _(default disabled)_
   - Electricity consumption: `W`
   - Electricity production: `W`
   - Electricity average: `W` (average use over the last 5min)
   - Electricity first measured: `date` _(default disabled)_
   - Electricity last measured: `date`
   - Electricity last measured production: `date`
   - Gas first measured: `date` _(default disabled)_
   - Gas last measured: `date`
</details>

### Zonneplan Energy contract related:
<details>
<summary>Sensors available if you have a Zonneplan energy contract</summary>
   
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
</details>
     
### Zonneplan Solar inverter:
<details>
<summary>Sensors available if you have a Zonneplan solar inverter</summary>
   
   - Yield total: `kWh`
   - First measured: `date` _(default disabled)_
   - Last measured value: `W`
   - Last measured: `date`
   - Powerplay enabled: `on/off` _(default disabled)_
   - Powerplay/power limit active: `on/off` _(default disabled)_
   - Powerplay total: `€` _(default disabled)_
   - Powerplay today: `€` _(default disabled)_
</details>

### Zonneplan Charge point/Laadpaal:
<details>
<summary>Sensors available if you have a Zonneplan charge point/laadpaal</summary>
   
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
  - Charge point session cost `€`
  - Charge point cost total `€`
  - Charge point flex result `€`
  - Charge point session average costs `€/kWh`
  - Charge point start mode _(default disabled)_
  - Charge point dynamic load desired distance `km`
  - Charge point dynamic load desired end time `datetime`
  - Charge point session start time `datetime`
  - Charge point session charged distance `km`
  - Charge point dynamic charging enabled `on/off`
  - Charge point dynamic charging flex enabled `on/off`
  - Charge point dynamic charging flex suppressed `on/off` _(default disabled)_
  - Buttons to start/stop charge
</details>

### Zonneplan Battery:
<details>
<summary>Sensors available if you have a Zonneplan Nexus battery</summary>

  - Avarage day: `€`
  - Battery cycles
  - Dynamic charging enabled `on/off`   
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
  - Grid congestion active `on/off`
  - Home optimization active `on/off`
  - Home optimization enabled `on/off`
  - Zelfconsumptie `on/off`
</details>

## Installation

### Install with HACS (recommended)

Ensure you have [HACS](https://hacs.xyz/) installed. 

[![Direct link to Zonneplan in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fsaris&repository=home-assistant-zonneplan-one)

1. Click the above My button or search HACS integrations for **Zonneplan**
1. Click `Install`
1. Restart Home Assistant
1. Continue with [setup](#setup)

### Install manually
<details>
   
1. Install this platform by creating a `custom_components` folder in the same folder as your configuration.yaml, if it doesn't already exist.
2. Create another folder `zonneplan_one` in the `custom_components` folder. 
3. Copy all files from `custom_components/zonneplan_one` into the newly created `zonneplan_one` folder.
</details>

### Installing main/beta version using HACS
<details>
   
1. Go to `HACS` => `Integrations`
1. Click on the three dots icon in right bottom of the **Zonneplan** card
1. Click `Reinstall`
1. Make sure `Show beta versions` is checked
1. Select version `main`
1. Click install and restart HA
</details>

## Setup
[![Open your Home Assistant instance and start setting up Zonneplan.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=zonneplan_one)
1. Click the above My button _(or navigate to `Configuration` -> `Integrations` -> `+ Add integration` and search for and select `Zonneplan ONE`)_
1. Enter you `emailaddress` you also use in the **Zonneplan** app
1. You will get an email to verify the login.
1. Click "Save"
1. Enjoy

## Setup Energy Dashboard
[![Open your Home Assistant instance and start setting up Energy sensors.](https://my.home-assistant.io/badges/config_energy.svg)](https://my.home-assistant.io/redirect/config_energy/)

#### Solar production
`Zonneplan Yield total` is what your panels produced

#### Grid consumption  
`Zonneplan Electricity consumption today` is what you used from the grid

#### Return to grid
`Zonneplan Electricity returned today` is what you returned to the grid

## Troubleshooting

If you run into issues during setup or when entries do not update anymore please enable debug logging and provide them when creating an issue.

1. Go to the integration

   [![Open your Home Assistant instance and show an integration.](https://my.home-assistant.io/badges/integration.svg)](https://my.home-assistant.io/redirect/integration/?domain=zonneplan_one)
2. Enable debug log by clicking `Enable debug logging`
3. Wait a few minutes for the integration to fetch new data
4. Disable debug logging again (same button as step 2)
5. Log will be presented for download
6. Be sure to remove sensitive data from the log before attaching it to a ticket
