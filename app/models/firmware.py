from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class UpdateStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    INSTALLING = "installing"
    INSTALLED = "installed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class FirmwareUpdate(BaseModel):
    id: str
    device_id: str
    from_version: str
    to_version: str
    status: UpdateStatus
    progress: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class FirmwareUpdateRequest(BaseModel):
    device_id: str
    to_version: str
    force: bool = False


class FirmwareMetadata(BaseModel):
    version: str
    size_bytes: int
    checksum: str
    release_notes: str
    min_compatible_version: str
    created_at: datetime
