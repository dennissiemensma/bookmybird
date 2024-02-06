# BookMyBird
**Unofficial** CLI tool for booking resources recurringly in DeskBird. Not affiliated in any way with DeskBird. Use at own risk.

## Setup
- Install Docker: https://docs.docker.com/engine/install/
- Configure you own env vars:
  ```shell
  cp compose.override.TEMPLATE.yaml compose.override.yaml
   ```
- Update the TODO-values in ``compose.override.yaml``
- Run:
  ```shell
  docker-compose up -d
  ```