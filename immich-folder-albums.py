#!/usr/bin/env python3
from pathlib import Path
from threading import Lock
import argparse
import logging
import sys
import os
import re

from scheduler import Scheduler
import requests
import yaml

import dotenv
dotenv.load_dotenv()

logging.basicConfig(encoding='utf-8', format="%(message)s")
logger = logging.getLogger(__name__)

lock = Lock()


class ImmichAPI:
    def __init__(self, api_url: str, token: str):
        self.api_url = api_url
        self._token = token
        self._headers = {
            "X-API-Key": self._token
        }

    def _get_request(self, endpoint: str, params: dict = {}) -> dict | list:
        r = requests.get(f"{self.api_url}{endpoint}", params=params, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def _post_request(self, endpoint: str, data) -> dict | list:
        r = requests.post(f"{self.api_url}{endpoint}", json=data, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def _put_request(self, endpoint: str, data) -> dict | list:
        r = requests.put(f"{self.api_url}{endpoint}", json=data, headers=self._headers)
        r.raise_for_status()
        return r.json()

    def _delete_request(self, endpoint: str):
        r = requests.delete(f"{self.api_url}{endpoint}", headers=self._headers)
        r.raise_for_status()

    def get_albums(self) -> list[dict]:
        return self._get_request("/albums")

    def get_album(self, album_id: str) -> dict:
        return self._get_request(f"/albums/{album_id}")

    def get_unique_paths(self) -> list[str]:
        return self._get_request("/view/folder/unique-paths")

    def get_folder_assets(self, path: str | Path) -> list[dict]:
        return self._get_request("/view/folder", {
            "path": str(path)
        })

    def create_album(self, name: str, description: str = "", assets_ids: list[str] = []) -> dict:
        data = {
            "albumName": name,
            "assetIds": assets_ids,
            "description": description,
        }
        return self._post_request("/albums", data)

    def album_add_assets(self, album_id: str, asset_ids: list[str]) -> list[dict]:
        data = {
            "ids": asset_ids
        }
        return self._put_request(f"/albums/{album_id}/assets", data)

    def delete_album(self, id: str):
        return self._delete_request(f"/albums/{id}")

    def delete_all_albums(self):
        albums = self.get_albums()
        albums_ids = [album['id'] for album in albums]
        for album_id in albums_ids:
            self.delete_album(album_id)


def find_album_by_name(album_name: str, albums: list[dict]) -> str:
    for album in albums:
        if album['albumName'] == album_name:
            return album['id']
    return None

def process_album_name(regexp: str|None, folder_name: str) -> str:
    if not regexp:
        return folder_name
    m = re.search(regexp, folder_name)
    return m.group() if m else folder_name

def run(args: argparse.Namespace, api: ImmichAPI):
    if not lock.acquire(blocking=False):
        return False

    if args.delete_all_albums:
        logger.debug("Deleting all albums...")
        api.delete_all_albums()

    logger.debug("Retrieving existing albums...")
    immich_albums: list[dict] = api.get_albums()

    unique_paths: list[Path] = [Path(p) for p in api.get_unique_paths()]
    potential_albums: set[Path] = {*unique_paths}

    for path in unique_paths:
        potential_albums.update(path.parents)

    albums: list[Path] = [p for p in potential_albums if (p / '.album').is_file()]

    for album_root in sorted(albums):
        logger.info(f"{album_root}")

        album_props: dict|None = yaml.safe_load(open(album_root / '.album'))
        album_props: dict = album_props if album_props else dict()
        album_name: str = album_props.get("name", process_album_name(args.album_regex, album_root.name))
        album_desc: str = album_props.get("description", "")
        album_order: str = album_props.get("order", "desc")
        recursive: bool = album_props.get("recursive", True)

        logger.info(f"\tAlbum name: '{album_name}'")
        if args.dry_run:
            continue

        album_id: str|None = find_album_by_name(album_name, immich_albums)
        if album_id is None:
            logger.info(f"\tCreating new album '{album_name}'")
            new_album: dict = api.create_album(album_name, album_desc)
            album_id: str = new_album['id']

        album_assets_ids: set[str] = {asset['id'] for asset in api.get_folder_assets(album_root)}

        if recursive:
            for path in unique_paths:
                if path.is_relative_to(album_root):
                    folder_assets: list[dict] = api.get_folder_assets(path)
                    album_assets_ids.update(asset['id'] for asset in folder_assets)

        album_assets_ids: list[str] = list(album_assets_ids)
        logger.info(f"\t{len(album_assets_ids)} assets found")

        if args.chunk_size:
            # Add assets to albums by chunks
            chunk_size: int = args.chunk_size
            chunks: list[list[str]] = [album_assets_ids[i:i + chunk_size] for i in range(0, len(album_assets_ids), chunk_size)]
        else:
            chunks: list[list[str]] = [album_assets_ids]

        for chunk in chunks:
            logger.debug(f"\tAdding {len(chunk)} assets to album '{album_name}' (album id: {album_id})")
            api.album_add_assets(album_id, chunk)

    lock.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", type=str, help="Immich API url (should typically end with '/api')")
    parser.add_argument("--api-key", type=str, help="Immich API key")
    parser.add_argument("-r", "--album-regex", type=str, help="Regexp to compute album name from folder name (default: just use folder name)")
    parser.add_argument("-s", "--chunk-size", type=int, help="Max number of assets to add to an album per API call (default: add all assets to each album in one API call). Sometimes the API call crash if there're too many assets in an album, try lowering this value if that's the case.")
    parser.add_argument("-v", "--verbose", action='count', help="Increase verbosity level (up to -vv)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Don't create new albums, just print the name of the albums that would be created if used with -v (useful to test your regex)")
    parser.add_argument("-X", "--delete-all-albums", action="store_true", help="Delete all existing immich albums before proceeding (even with -n/--dry-run)")
    parser.add_argument("-c", "--cron-expr", type=str, help="Cron expression for scheduled run")

    parser.set_defaults(
        api_url =           os.getenv("IMMICH_API_URL"),
        api_key =           os.getenv("IMMICH_API_KEY"),
        album_regex =       os.getenv("ALBUM_NAME_REGEX"),
        chunk_size =        os.getenv("API_CHUNK_SIZE"),
        verbose =           int(os.getenv("VERBOSE", 0)),
        dry_run =           bool(os.getenv("DRY_RUN", False)),
        delete_all_albums = bool(os.getenv("DELETE_ALL_ALBUMS", False)),
        cron_expr =         os.getenv("CRON_EXPRESSION"),
    )

    args = parser.parse_args()

    if args.verbose >= 1: logger.setLevel(logging.INFO)
    if args.verbose >= 2: logger.setLevel(logging.DEBUG)

    if not all((args.api_url, args.api_key)):
        print("The --api-url and --api-key parameters are required. Please specify them or use the IMMICH_API_URL and IMMICH_API_KEY environment variables.", file=sys.stderr)
        exit(1)

    api = ImmichAPI(
        args.api_url,
        args.api_key
    )

    if args.cron_expr:
        scheduler = Scheduler(60)
        scheduler.add('run', args.cron_expr, run, (args, api))
        scheduler.start()
    else:
        run(args, api)


if __name__ == '__main__':
    main()
