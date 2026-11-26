from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.render import Render


T = TypeVar("T", bound="RenderPage")


@_attrs_define
class RenderPage:
    """
    Attributes:
        data (list[Render]):
        page (int):
        per_page (int):
        has_more (bool):
    """

    data: list[Render]
    page: int
    per_page: int
    has_more: bool
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:

        data = []
        for data_item_data in self.data:
            data_item = data_item_data.to_dict()
            data.append(data_item)

        page = self.page

        per_page = self.per_page

        has_more = self.has_more

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "data": data,
                "page": page,
                "per_page": per_page,
                "has_more": has_more,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.render import Render  # noqa: PLC0415

        d = dict(src_dict)
        data = []
        _data = d.pop("data")
        for data_item_data in _data:
            data_item = Render.from_dict(data_item_data)

            data.append(data_item)

        page = d.pop("page")

        per_page = d.pop("per_page")

        has_more = d.pop("has_more")

        render_page = cls(
            data=data,
            page=page,
            per_page=per_page,
            has_more=has_more,
        )

        render_page.additional_properties = d
        return render_page

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
