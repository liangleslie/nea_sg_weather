# NEA Singapore Weather Integration for Home Assistant

Home Assistant Integration to get current weather information directly from Data.gov.sg weather API published by Singapore National Enviroment Agency (SG NEA)

![image](https://user-images.githubusercontent.com/57534857/142906976-9f28571f-290f-42e1-85a0-68ee23f917d8.png)

![image](https://user-images.githubusercontent.com/57534857/142907008-1e5b1f76-c054-4797-b73f-8ad0d22e6b4c.png)

## Installation

Add this integration to Home Assistant using HACS, or copy everything in `custom_components/nea_sg_weather` to your `custom_components` folder in your Home Assistant `config` folder. 

Follow the integration config flow to set up the following entities:
- `weather`: weather entity with 4 day forecasts
- `area` (town) sensors: current weather conditions for up to 47 areas/towns in Singapore 
- `region` sensors: 24 weather condition forecast for North/South/East/West/Central regions of Singapore
- `rain` camera: rain map overlay that is updated every 5 minutes from NEA
- `pm25` sensors: 5 pm2.5 sensors for North/South/East/West/Central regions of Singapore
- `uv_index` sensor: 1 uv index for Singapore

## Weather Map Overlays

Several `yaml` files are included to help you quickly set up a weather map card on Lovelace UI.
![image](https://user-images.githubusercontent.com/57534857/142712510-cabf3214-09c2-4fda-8d43-ff230aebd91c.png)

For the overlays to display properly, you will need the `area`, `region` and `rain` entities activated in the config flow.

1. `input_boolean.yaml`: to set up `input_boolean` toggles for the map overlays
2. `automations.yaml`: automations to manage how the map toggles work
3. `lovelace.yaml`: preset card config to display the weather map card

Instructions for how to integrate the `yaml` files are included in the various files in the `nea_sg_weather/yaml` folder.
