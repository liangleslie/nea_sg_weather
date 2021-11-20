# NEA Singapore Weather Integration for Home Assistant


Home Assistant Integration to get current weather information directly from Data.gov.sg weather API published by Singapore National Enviroment Agency (SG NEA)

Add this integration to Home Assistant using HACS, or copy everything in `custom_components/nea_sg_weather` to your `custom_components` folder in your Home Assistant `config` folder. 

Follow the integration config flow to set up the following entities:
- `weather`: weather entity with 4 day forecasts
- `area` (town) sensors: current weather conditions for up to 47 areas/towns in Singapore 
- `region` sensors: 24 weather condition forecast for North/South/East/West/Central regions of Singapore
- `rain` camera: rain map overlay that is updated every 5 minutes from NEA


## Rain Map Overlays

