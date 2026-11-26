from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar
from uuid import UUID

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.render_queued_status import RenderQueuedStatus, check_render_queued_status

T = TypeVar("T", bound="RenderQueued")


@_attrs_define
class RenderQueued:
    """
    Attributes:
        render_id (UUID):
        status (RenderQueuedStatus):
        status_url (str): Path of the status endpoint, relative to the API base URL.
    """

    render_id: UUID
    status: RenderQueuedStatus
    status_url: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        render_id = str(self.render_id)

        status: str = self.status

        status_url = self.status_url

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "render_id": render_id,
                "status": status,
                "status_url": status_url,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        render_id = UUID(d.pop("render_id"))

        status = check_render_queued_status(d.pop("status"))

        status_url = d.pop("status_url")

        render_queued = cls(
            render_id=render_id,
            status=status,
            status_url=status_url,
        )

        render_queued.additional_properties = d
        return render_queued

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
