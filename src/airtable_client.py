import re
from urllib.parse import urlparse

from pyairtable import Api


class AirTableClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("AIRBASE_TOKEN fehlt. Bitte in der .env setzen.")
        self.api = Api(api_key=api_key, timeout=(10, 30))

    def get_table(self, url: str):
        base_id = ""
        table_name = ""
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "airtable.com",
            "www.airtable.com",
        }:
            raise ValueError(
                "Bitte eine https://airtable.com/... Tabellen-URL angeben."
            )
        for part in parsed.path.split("/"):
            if re.fullmatch(r"app[A-Za-z0-9]+", part):
                base_id = part
            if re.fullmatch(r"tbl[A-Za-z0-9]+", part):
                table_name = part

        if len(base_id) == 0 or len(table_name) == 0:
            raise ValueError("Invalid URL: cant read Base_id and Table_name")

        return self.api.table(base_id=base_id, table_name=table_name)
