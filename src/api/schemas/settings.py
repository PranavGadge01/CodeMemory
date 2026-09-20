from typing import Optional
from api.schemas.common import BaseCamelModel

class SettingsOut(BaseCamelModel):
    leetcode_connected: bool
    autosync_enabled: bool
    data_dir: str
    version: str
