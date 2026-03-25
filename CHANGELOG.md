v2.5.4

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
