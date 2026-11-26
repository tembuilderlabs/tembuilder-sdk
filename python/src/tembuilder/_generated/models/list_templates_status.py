from typing import Literal

ListTemplatesStatus = Literal["all", "draft", "published"]

LIST_TEMPLATES_STATUS_VALUES: set[ListTemplatesStatus] = {
    "all",
    "draft",
    "published",
}


def check_list_templates_status(value: str) -> ListTemplatesStatus:
    if value in LIST_TEMPLATES_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_TEMPLATES_STATUS_VALUES!r}")
