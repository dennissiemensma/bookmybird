# BookMyBird
**Unofficial** CLI tool for booking resources recurringly in DeskBird. Not affiliated in any way with DeskBird. Use at own risk.

## Setup
- Install Docker: https://docs.docker.com/engine/install/
- Configure you own env vars:
  ```shell
  cp compose.override.TEMPLATE.yaml compose.override.yaml
   ```
- Preferences: Update ``BOOK_DAYS_AHEAD`` in ``compose.override.yaml``. 
  - *Please note that a value of ``4`` results in the tool to target the single day 4 days ahead. 
  - It's **not** a range to book today and the four consecutive days after as well. It will book one targeted day every time and does the same again after every midnight. 

- Deskbird stuff: Update ``DESKBIRD_RESOURCE_ID``, ``DESKBIRD_WORKSPACE_ID`` and ``DESKBIRD_USER_ID`` in ``compose.override.yaml``
- Auth stuff: Update ``DESKBIRD_GOOGLE_AUTH_KEY`` and ``DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN`` in ``compose.override.yaml``
- Update the zone item IDs for ``DESKBIRD_ZONE_ITEM_IDS_ON_*`` in ``compose.override.yaml``
  - The latter may be multiple zone item IDs, comma separated. 
  - Zone item IDs for your workspace will also be retrieved on startup and logged as output.  
- Run:
  ```shell
  docker-compose up -d
  ```
