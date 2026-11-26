from __future__ import annotations

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
    """

    render_id: UUID
    status: str
    duration_ms: int | Unset = UNSET
    error_message: str | Unset = UNSET
    download_url: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        render_id = str(self.render_id)

        status = self.status

        duration_ms = self.duration_ms

        error_message = self.error_message

        download_url = self.download_url

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

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        render_id = UUID(d.pop("render_id"))

        status = d.pop("status")

        duration_ms = d.pop("duration_ms", UNSET)

        error_message = d.pop("error_message", UNSET)

        download_url = d.pop("download_url", UNSET)

        render_status = cls(
            render_id=render_id,
            status=status,
            duration_ms=duration_ms,
            error_message=error_message,
            download_url=download_url,
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
