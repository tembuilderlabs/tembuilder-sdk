from typing import Literal

ListRendersStatus = Literal["all", "failed", "pending", "quota_exceeded", "success"]

LIST_RENDERS_STATUS_VALUES: set[ListRendersStatus] = {
    "all",
    "failed",
    "pending",
    "quota_exceeded",
    "success",
}


def check_list_renders_status(value: str) -> ListRendersStatus:
    if value in LIST_RENDERS_STATUS_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {LIST_RENDERS_STATUS_VALUES!r}")
