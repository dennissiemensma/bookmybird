# BookMyBird
**Unofficial** CLI tool for booking resources recurringly in DeskBird. Not affiliated in any way with DeskBird. Use at own risk.



## Setup
### Docker
- Install Docker: https://docs.docker.com/engine/install/

### Config 
- Configure your own env vars:
  ```shell
  cp compose.override.TEMPLATE.yaml compose.override.yaml
   ```
  
#### Deskbird settings
- Company/account settings: Update in ``compose.override.yaml``
  - ``DESKBIRD_RESOURCE_ID`` (*company*)
  - ``DESKBIRD_WORKSPACE_ID`` (*company*)
  - ``DESKBIRD_USER_ID`` (*your account*)

- Auth settings: Update in ``compose.override.yaml``:
  - ``DESKBIRD_GOOGLE_AUTH_KEY`` (*your account*)
  - ``DESKBIRD_GOOGLE_AUTH_REFRESH_TOKEN`` (*your account*)


#### Tool settings
- Booking preferences: Update in ``compose.override.yaml``:
  - ``BOOK_DAYS_AHEAD``
    - Please note that a value of ``6`` results in the tool to target the **single day** six days ahead. You may or may not be limited by your company's restrictions set in DeskBird. 
    - E.g. if it's just past midnight, early on a **Wednesday**, a `BOOK_DAYS_AHEAD=6` will have this tool try to book your preferences for **next week Tuesday**.
    - Additionally, on every startup/restart, it will try to book the targeted day **once**. Both for convenience and debugging.
  
  - ``DESKBIRD_ZONE_ITEM_IDS_ON_*`` (*per weekday*)
    - The latter may be multiple zone item IDs, comma separated. 
    - Zone item IDs for your workspace will also be retrieved on startup and logged as output.  


### Finishing up
- Run:
  ```shell
  docker-compose up -d
  ```
- Logs:
  ```shell
  docker logs bookmybird-app -f -t
  ```
