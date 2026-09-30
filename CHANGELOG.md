Unreleased

- Added a **Reconfigure** option to change which entities an instance sets
  up (weather entity, areas, region sensors, rain, scan interval, timeout)
  without removing and re-adding it. The name and prefix are kept, so entity
  IDs do not change
- Entities and region devices switched off are removed when the integration
  reloads instead of staying behind as orphans
- The example weather map card (`yaml/lovelace.yaml`) can show NEA's
  landmarks, townships, MRT and expressway overlays and the rain intensity
  legend, with toggles in `yaml/input_boolean.yaml`; the rain layer uses
  NEA's opacity (0.5)
- Added pollutant concentration sensors per region (PM2.5 and PM10 24-hour,
  SO2 24-hour, O3 and CO 8-hour max, NO2 1-hour max) from the PSI response,
  so the values get history and statistics. Created disabled by default
  (`sensor.<prefix>_pm10_24h_central` etc.); enable the ones you want
- The 1-hour PM2.5 sensor now uses Home Assistant's `UnitOfDensity` unit
- Entity names follow Home Assistant's naming model: each instance's device is
  named after the instance (was "Weather forecast coordinator"), and region
  entities sit on one child device per region ("Central Singapore", …).
  Friendly names read e.g. "Singapore Weather UV index" or "Central Singapore
  PSI (24-hour)" instead of "Weather forecast coordinator PSI in Central
  Singapore". Entity IDs are unchanged.
- Rainfall sensors are named after the station location (e.g. "Rainfall at
  Tanjong Rhu") instead of the station ID
- Requires Home Assistant 2026.9 or newer

v2.7.0

- Updated version to 2.7.0 for HACS compatibility

v2.6.3

- Graceful API failure handling: per-request 10-second timeout; primary endpoint
  errors automatically fall back to secondary endpoint where available
- Stale data preservation: if an individual API call fails during a coordinator
  update, the last known value is retained instead of the entire integration
  turning Unavailable
- Fixed Wind calculation crash (ZeroDivisionError) when no matching station
  pairs are returned by the API
- Fixed CI: corrected pytest-homeassistant-custom-component version constraint
  (1.3.0 does not exist; pinned to 0.13.x for Python 3.12)

v2.5.3

- migrate all v1 api data to v2

v2.4.6

- added additional sensors (uv and pm2.5) from nea

v2.4.2

- added uv data from nea
