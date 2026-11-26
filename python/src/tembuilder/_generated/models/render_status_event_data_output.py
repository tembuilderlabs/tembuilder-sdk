from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="RenderStatusEventDataOutput")


@_attrs_define
class RenderStatusEventDataOutput:
    """
    Attributes:
        content_type (str):
        size_bytes (int):
        download_url (str):
    """

    content_type: str
    size_bytes: int
    download_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        content_type = self.content_type

        size_bytes = self.size_bytes

        download_url = self.download_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "content_type": content_type,
                "size_bytes": size_bytes,
                "download_url": download_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        content_type = d.pop("content_type")

        size_bytes = d.pop("size_bytes")

        download_url = d.pop("download_url")

        render_status_event_data_output = cls(
            content_type=content_type,
            size_bytes=size_bytes,
            download_url=download_url,
        )

        render_status_event_data_output.additional_properties = d
        return render_status_event_data_output

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
