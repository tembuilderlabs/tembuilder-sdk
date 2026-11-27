from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="RenderStatus")


@_attrs_define
class RenderStatus:
    """
    Attributes:
        render_id (UUID):
        status (str): `pending`, or a terminal state: `success`, `failed`, `quota_exceeded`.
        duration_ms (int | Unset):
        error_message (str | Unset):
        download_url (str | Unset): Path of the download endpoint, present when status is `success`.
        file_url (str | Unset): Signed URL that serves the PDF directly from storage, present when
            status is `success`. Send no API key to it. Valid until
            `file_url_expires_at`; fetch the status again for a fresh one.
        file_url_expires_at (datetime.datetime | Unset): When `file_url` stops working (15 minutes after this response).
    """

    render_id: UUID
    status: str
    duration_ms: int | Unset = UNSET
    error_message: str | Unset = UNSET
    download_url: str | Unset = UNSET
    file_url: str | Unset = UNSET
    file_url_expires_at: datetime.datetime | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        render_id = str(self.render_id)

        status = self.status

        duration_ms = self.duration_ms

        error_message = self.error_message

        download_url = self.download_url

        file_url = self.file_url

        file_url_expires_at: str | Unset = UNSET
        if not isinstance(self.file_url_expires_at, Unset):
            file_url_expires_at = self.file_url_expires_at.isoformat()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "render_id": render_id,
                "status": status,
            }
        )
        if duration_ms is not UNSET:
            field_dict["duration_ms"] = duration_ms
        if error_message is not UNSET:
            field_dict["error_message"] = error_message
        if download_url is not UNSET:
            field_dict["download_url"] = download_url
        if file_url is not UNSET:
            field_dict["file_url"] = file_url
        if file_url_expires_at is not UNSET:
            field_dict["file_url_expires_at"] = file_url_expires_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        render_id = UUID(d.pop("render_id"))

        status = d.pop("status")

        duration_ms = d.pop("duration_ms", UNSET)

        error_message = d.pop("error_message", UNSET)

        download_url = d.pop("download_url", UNSET)

        file_url = d.pop("file_url", UNSET)

        _file_url_expires_at = d.pop("file_url_expires_at", UNSET)
        file_url_expires_at: datetime.datetime | Unset
        if isinstance(_file_url_expires_at, Unset):
            file_url_expires_at = UNSET
        else:
            file_url_expires_at = datetime.datetime.fromisoformat(_file_url_expires_at)

        render_status = cls(
            render_id=render_id,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            download_url=download_url,
            file_url=file_url,
            file_url_expires_at=file_url_expires_at,
        )

        render_status.additional_properties = d
        return render_status

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
