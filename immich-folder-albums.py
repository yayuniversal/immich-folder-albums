#!/usr/bin/env python3
from pathlib import Path
import requests
import argparse
import logging
import yaml
import os

import dotenv
dotenv.load_dotenv()

logging.basicConfig(encoding='utf-8')
logger = logging.getLogger(__name__)


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


def main():
    api = ImmichAPI(
        os.getenv('IMMICH_API_URL'),
        os.getenv('IMMICH_API_KEY')
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--delete-all-albums", default=False, action="store_true", help="Delete all existing immich albums before proceeding")
    parser.add_argument("-s", "--chunk-size", default=None, type=int, help="Max number of assets to add to an album per API call (default: add all assets to each album in one API call. Sometimes the API call crash if there're too many assets in an album, try lowering this value if that's the case.")
    parser.add_argument("-v", "--verbose", default=0, action='count', help="Increase verbosity level (up to -vv)")
    args = parser.parse_args()

    if args.verbose >= 1: logger.setLevel(logging.INFO)
    if args.verbose >= 2: logger.setLevel(logging.DEBUG)

    if args.delete_all_albums:
        logger.info("Deleting all albums...")
        api.delete_all_albums()

    immich_albums: list[dict] = api.get_albums()

    unique_paths: list[Path] = [Path(p) for p in api.get_unique_paths()]
    potential_albums: set[Path] = {*unique_paths}

    for path in unique_paths:
        potential_albums.update(path.parents)

    albums: list[Path] = [p for p in potential_albums if (p / '.album').is_file()]

    for album_root in sorted(albums):
        logger.info(f"Album '{album_root}'")

        album_props: dict|None = yaml.safe_load(open(album_root / '.album'))
        album_props: dict = album_props if album_props else dict()
        album_name: str = album_props.get("name", album_root.name)
        album_desc: str = album_props.get("description", "")
        album_order: str = album_props.get("order", "desc")
        recursive: bool = album_props.get("recursive", True)

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


if __name__ == '__main__':
    main()
