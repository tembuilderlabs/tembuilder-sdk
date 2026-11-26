from __future__ import annotations

import datetime
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.render_status_event_type import RenderStatusEventType, check_render_status_event_type

if TYPE_CHECKING:
    from ..models.render_status_event_data import RenderStatusEventData


T = TypeVar("T", bound="RenderStatusEvent")


@_attrs_define
class RenderStatusEvent:
    """Body of the `renders.status` webhook. Verify the `Tembuilder-Signature`
    header against the raw body before parsing (the SDKs provide
    `verifyWebhook`).

        Attributes:
            api_version (str):  Example: 2026-09-12.
            type_ (RenderStatusEventType):
            occurred_at (datetime.datetime):
            data (RenderStatusEventData):
    """

    api_version: str
    type_: RenderStatusEventType
    occurred_at: datetime.datetime
    data: RenderStatusEventData
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        api_version = self.api_version

        type_: str = self.type_

        occurred_at = self.occurred_at.isoformat()

        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "api_version": api_version,
                "type": type_,
                "occurred_at": occurred_at,
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.render_status_event_data import RenderStatusEventData  # noqa: PLC0415

        d = dict(src_dict)
        api_version = d.pop("api_version")

        type_ = check_render_status_event_type(d.pop("type"))

        occurred_at = datetime.datetime.fromisoformat(d.pop("occurred_at"))

        data = RenderStatusEventData.from_dict(d.pop("data"))

        render_status_event = cls(
            api_version=api_version,
            type_=type_,
            occurred_at=occurred_at,
            data=data,
        )

        render_status_event.additional_properties = d
        return render_status_event

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
