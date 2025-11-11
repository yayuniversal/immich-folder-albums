![Python 3.13](https://img.shields.io/badge/python-3.13-blue)

# immich-folder-albums
Python script to create Immich albums from folders in external libraries. It looks for folders containing a `.album` file and creates a corresponding Immich album.

Tested with Python 3.13; should work with newer versions (*may* work with previous versions as well, but untested).


## Requirements
- Install the dependencies (in a virtualenv):
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
- The script does not do any path translation, so your external library must be mounted at the same path that Immich accesses it inside the container. Use `mount --bind` if that's not the case:
    ```shell
    mount --bind <src> <target>
    ```
    For example, if in immich's `docker-compose.yml`, you mounted your external library like this:
    ```yaml
      ...
      volumes:
        - /path/to/my/pictures:/photos
    ```
    then use:
    ```shell
    mount --mkdir --bind /path/to/my/pictures /photos
    ```

- Create a `.album` file in each folder that you want an Immich album to be created for.


## How to use
```
usage: immich-folder-albums.py [-h] [--api-url API_URL] [--api-key API_KEY] [-r ALBUM_REGEX] [-s CHUNK_SIZE] [-v] [-n] [-X]

options:
  -h, --help            show this help message and exit
  --api-url API_URL     Immich API url (should typically end with '/api')
  --api-key API_KEY     Immich API key
  -r, --album-regex ALBUM_REGEX
                        Regexp to compute album name from folder name (default: just use folder name)
  -s, --chunk-size CHUNK_SIZE
                        Max number of assets to add to an album per API call (default: add all assets to each album in one API call). Sometimes the API call crash if there're too many assets in an album, try lowering this value if that's the case.
  -v, --verbose         Increase verbosity level (up to -vv)
  -n, --dry-run         Don't create new albums, just print the name of the albums that would be created (useful to test your regex)
  -X, --delete-all-albums
                        Delete all existing immich albums before proceeding (even with -n/--dry-run)
```

All the CLI parameters can also be set via environment variables:

| CLI parameter         | Environment variable    | required | default                                      |
| --------------------- | ----------------------- | :------: | -------------------------------------------- |
| `--api-url`           | `IMMICH_API_URL`        |    x     |                                              |
| `--api-key`           | `IMMICH_API_KEY`        |    x     |                                              |
| `--album-regex`       | `ALBUM_NAME_REGEX`      |          | Use the folder name                          |
| `--chunk-size`        | `API_CHUNK_SIZE`        |          | Add all assets to each album in one API call |
| `--verbose`           | `VERBOSE`               |          | 0 (up to 2)                                  |
| `--dry-run`           | `DRY_RUN`[^1]           |          |                                              |
| `--delete-all-albums` | `DELETE_ALL_ALBUMS`[^1] |          |                                              |

[^1]: Enabled if set and non-empty. So even if `DELETE_ALL_ALBUMS=0`, all existing albums will be deleted.


## `.album` files
Each `.album` file can be empty, but it is actually treated as a YAML file and can contain some properties (all optional):

```yaml
name: Album name
description: Album description
recursive: yes/no
```

By default, the album name is taken from the folder name, the album description is empty, and the assets are added recursively (pictures/videos in subfolders are added to the album as well).
