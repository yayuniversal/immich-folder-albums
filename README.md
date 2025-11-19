![Python 3.13](https://img.shields.io/badge/python-3.13-blue)

# immich-folder-albums
Python script to create Immich albums from folders in external libraries. It looks for folders containing a `.album` file and creates a corresponding Immich album.

Tested with Python 3.13; should work with newer versions (*may* work with previous versions as well, but untested).

The script can be used either with Docker (useful for scheduled runs alongside your Immich stack), or manually on the command line.


## Prepare your library
Create a `.album` file in each folder that you want turned into an Immich album. This script will look for them and create corresponding albums. It will **not** create albums for every existing folder; only the ones containing a `.album` file.


## Use with Docker compose
The repository includes an example [`docker-compose.yml`](docker-compose.yml); download it and adapt values.

```yaml
services:
  immich-folder-albums:
    image: ghcr.io/yayuniversal/immich-folder-albums
    container_name: immich-folder-albums
    volumes:
      # mount external library at the same mountpoint than in the Immich container
      - /path/to/your/photos:/path/inside/immich:ro
    environment:
      IMMICH_API_URL: https://immich.example.com/api
      IMMICH_API_KEY: your_api_key
      VERBOSE: 1  # 0 = quiet, 1 = info, 2 = debug
      CRON_EXPRESSION: "0 2 * * *"  # run daily at 02:00
      # ALBUM_NAME_REGEX: "your_regex"
      # API_CHUNK_SIZE: 1000
      # DRY_RUN: 1
      # DELETE_ALL_ALBUMS: 1
```

1. Copy the provided `docker-compose.yml`
2. Configure environment variables (see below)
3. Ensure the external photo library is mounted at the same path inside the container than inside the Immich container (see "External library mounting" below)

Then start the container:
```shell
docker compose up -d
```

### Environment variables

- `IMMICH_API_URL` (required) — Base Immich API URL (typically ends with `/api`)
- `IMMICH_API_KEY` (required) — Immich API key
- `ALBUM_NAME_REGEX` — Regex to transform folder name into album name
- `API_CHUNK_SIZE` — Max assets per API call (useful for very large albums)
- `VERBOSE` — 0 = quiet (default), 1 = info, 2 = debug
- `DRY_RUN` — if set and non-empty, do not create or add to albums
- `DELETE_ALL_ALBUMS` — if set and non-empty, delete all existing albums before creating new ones. WARNING: destructive.
- `CRON_EXPRESSION` — run schedule (standard cron expression). If unset, the script runs once and exits.

Important:
- `DRY_RUN` and `DELETE_ALL_ALBUMS` are considered enabled when the variable exists and is non-empty — even the value `0` will be treated as enabled.
- `DELETE_ALL_ALBUMS` will delete all existing albums **EVEN IF** `DRY_RUN` is enabled! So by using `DELETE_ALL_ALBUMS` with `DRY_RUN`, you'll wipe all your albums without creating new ones, ending up with 0 Immich albums.


## Manual use
### Requirements
- Install the dependencies (preferably in a virtualenv):
    ```shell
    virtualenv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
- Fill the `.env` file with your Immich API key and URL:
    ```ini
    IMMICH_API_URL=<your_immich_url>/api
    IMMICH_API_KEY=<your_immich_api_key>
    ```
- The script does not do any path translation, so your external library must be mounted at the same path that Immich accesses it inside the container (see "External library mounting" below). Use `mount --bind` if that's not the case:
    ```shell
    mount --bind <src> <target>
    ```
    For example, if in the `docker-compose.yml` for Immich your external library is mounted like this:
    ```yaml
      ...
      volumes:
        - /path/to/my/pictures:/photos
    ```
    then use:
    ```shell
    mount --mkdir --bind /path/to/my/pictures /photos
    ```

### Usage
```
usage: immich-folder-albums.py [-h] [--api-url API_URL] [--api-key API_KEY] [-r ALBUM_REGEX] [-s CHUNK_SIZE] [-v] [-n] [-X] [-c CRON_EXPR]

options:
  -h, --help            show this help message and exit
  --api-url API_URL     Immich API url (should typically end with '/api')
  --api-key API_KEY     Immich API key
  -r, --album-regex ALBUM_REGEX
                        Regexp to compute album name from folder name (default: just use folder name)
  -s, --chunk-size CHUNK_SIZE
                        Max number of assets to add to an album per API call (default: add all assets to each album in one API call). Sometimes the API call crash if there're too many assets in an album, try lowering this value if that's the case.
  -v, --verbose         Increase verbosity level (up to -vv)
  -n, --dry-run         Don't create new albums, just print the name of the albums that would be created if used with -v (useful to test your regex)
  -X, --delete-all-albums
                        Delete all existing immich albums before proceeding (even with -n/--dry-run)
  -c, --cron-expr CRON_EXPR
                        Cron expression for scheduled run
```

All CLI options can also be set via environment variables:

| CLI parameter               | Environment variable    | required | default                                      |
| --------------------------- | ----------------------- | :------: | -------------------------------------------- |
| `--api-url`                 | `IMMICH_API_URL`        |    x     |                                              |
| `--api-key`                 | `IMMICH_API_KEY`        |    x     |                                              |
| `-r`, `--album-regex`       | `ALBUM_NAME_REGEX`      |          | Use the folder name as album name            |
| `-s`, `--chunk-size`        | `API_CHUNK_SIZE`        |          | Add all assets to each album in one API call |
| `-v`, `--verbose`           | `VERBOSE`               |          | 0 (up to 2, or `-vv`)                        |
| `-n`, `--dry-run`           | `DRY_RUN`[^1]           |          |                                              |
| `-X`, `--delete-all-albums` | `DELETE_ALL_ALBUMS`[^1] |          | Add new assets to existing album if present  |
| `-c`, `--cron-expr`         | `CRON_EXPRESSION`       |          | Run once and exit                            |

[^1]: Enabled if set and non-empty. So even if `DELETE_ALL_ALBUMS=0`, all existing albums will be deleted.


## External library mounting

The script does not translate paths. The mounted path inside the container must match the path Immich uses to access the external library. If Immich accesses your library at `/photos`, the script must also see the library at `/photos`.

When using Docker compose, use the same `host:container` volume mapping for your external library than in Immich.
If you have multiple external libraries, mount them all at the same mountpoints than the ones used for Immich.

Mounting read-only (`:ro`) is recommended because the script only reads `.album` files.

When using the script directly on the CLI (without Docker), bind mount your external library directory beforehand to make it appear at the same location Immich sees it:
```shell
mount --mkdir --bind <external_library_folder> <location_inside_immich>
```


## `.album` file format

Place a `.album` file in any folder you want turned into an Immich album. The file can be empty, but is actually parsed as YAML and can contain some properties (all fields are optional):

```yaml
name: My Album                # album name (defaults to folder name)
description: Description      # album description (default empty)
recursive: yes/no             # include assets from subfolders (default: true)
```

If the `.album` file is empty, the folder name is used as the album name, the album description is empty, and the assets are added recursively (pictures/videos in subfolders are added to the album as well).


## Scheduling behavior

- If the `CRON_EXPRESSION` environment variable is set or the `-c,--cron-expr` CLI parameter is used, the container runs continuously and executes the script on the specified schedule.
- If not set, the script runs once at container start and the container exits.

Example cron expression: `0 2 * * *` runs daily at 02:00.

Check [crontab.guru](https://crontab.guru/) for help with cron expressions.


## Dry-run

- Use `DRY_RUN` or `-n,--dry-run` when testing album names/regex; the script will not create or add to albums when dry-run is enabled. Useful with `VERBOSE` / `-v,--verbose` to print the preprocessed album names.
- Beware: dry run doesn't prevent deletion of all existing albums when `DELETE_ALL_ALBUMS` / `-X,--delete-all-albums` is enabled!


## Troubleshooting

- Missing albums / zero assets: check that the container sees the same paths than Immich and that `.album` files exist and are readable.
- API errors: check `IMMICH_API_URL` and `IMMICH_API_KEY`.
- Large albums fail: lower `API_CHUNK_SIZE`.
