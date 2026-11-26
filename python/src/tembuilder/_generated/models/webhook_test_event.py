from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.webhook_test_event_type import WebhookTestEventType, check_webhook_test_event_type

if TYPE_CHECKING:
    from ..models.webhook_test_event_data import WebhookTestEventData


T = TypeVar("T", bound="WebhookTestEvent")


@_attrs_define
class WebhookTestEvent:
    """Body sent by "Send test" on a webhook endpoint in the app.

    Attributes:
        api_version (str):  Example: 2026-09-12.
        type_ (WebhookTestEventType):
        data (WebhookTestEventData):
    """

    api_version: str
    type_: WebhookTestEventType
    data: WebhookTestEventData
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        api_version = self.api_version

        type_: str = self.type_

        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "api_version": api_version,
                "type": type_,
                "data": data,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.webhook_test_event_data import WebhookTestEventData  # noqa: PLC0415

        d = dict(src_dict)
        api_version = d.pop("api_version")

        type_ = check_webhook_test_event_type(d.pop("type"))

        data = WebhookTestEventData.from_dict(d.pop("data"))

        webhook_test_event = cls(
            api_version=api_version,
            type_=type_,
            data=data,
        )

        webhook_test_event.additional_properties = d
        return webhook_test_event

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
