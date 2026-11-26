from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import Any, TypeVar, cast
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Render")


@_attrs_define
class Render:
    """
    Attributes:
        id (UUID):
        short_id (str):
        status (str): `pending`, `success`, `failed` or `quota_exceeded`.
        template_id (UUID):
        template_version (int):
        variant (None | str):
        duration_ms (int | None):
        error_message (None | str):
        started_at (datetime.datetime):
        completed_at (datetime.datetime | None):
        status_url (str):
        download_url (None | str):
    """

    id: UUID
    short_id: str
    status: str
    template_id: UUID
    template_version: int
    variant: None | str
    duration_ms: int | None
    error_message: None | str
    started_at: datetime.datetime
    completed_at: datetime.datetime | None
    status_url: str
    download_url: None | str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = str(self.id)

        short_id = self.short_id

        status = self.status

        template_id = str(self.template_id)

        template_version = self.template_version

        variant: None | str
        variant = self.variant

        duration_ms: int | None
        duration_ms = self.duration_ms

        error_message: None | str
        error_message = self.error_message

        started_at = self.started_at.isoformat()

        completed_at: None | str
        if isinstance(self.completed_at, datetime.datetime):
            completed_at = self.completed_at.isoformat()
        else:
            completed_at = self.completed_at

        status_url = self.status_url

        download_url: None | str
        download_url = self.download_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "short_id": short_id,
                "status": status,
                "template_id": template_id,
                "template_version": template_version,
                "variant": variant,
                "duration_ms": duration_ms,
                "error_message": error_message,
                "started_at": started_at,
                "completed_at": completed_at,
                "status_url": status_url,
                "download_url": download_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = UUID(d.pop("id"))

        short_id = d.pop("short_id")

        status = d.pop("status")

        template_id = UUID(d.pop("template_id"))

        template_version = d.pop("template_version")

        def _parse_variant(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        variant = _parse_variant(d.pop("variant"))

        def _parse_duration_ms(data: object) -> int | None:
            if data is None:
                return data
            return cast(int | None, data)

        duration_ms = _parse_duration_ms(d.pop("duration_ms"))

        def _parse_error_message(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        error_message = _parse_error_message(d.pop("error_message"))

        started_at = datetime.datetime.fromisoformat(d.pop("started_at"))

        def _parse_completed_at(data: object) -> datetime.datetime | None:
            if data is None:
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                completed_at_type_0 = datetime.datetime.fromisoformat(data)

                return completed_at_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.datetime | None, data)

        completed_at = _parse_completed_at(d.pop("completed_at"))

        status_url = d.pop("status_url")

        def _parse_download_url(data: object) -> None | str:
            if data is None:
                return data
            return cast(None | str, data)

        download_url = _parse_download_url(d.pop("download_url"))

        render = cls(
            id=id,
            short_id=short_id,
            status=status,
            template_id=template_id,
            template_version=template_version,
            variant=variant,
            duration_ms=duration_ms,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
            status_url=status_url,
            download_url=download_url,
        )

        render.additional_properties = d
        return render

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
