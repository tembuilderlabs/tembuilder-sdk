from typing import Literal

WebhookTestEventType = Literal["webhook.test"]

WEBHOOK_TEST_EVENT_TYPE_VALUES: set[WebhookTestEventType] = {
    "webhook.test",
}


def check_webhook_test_event_type(value: str) -> WebhookTestEventType:
    if value in WEBHOOK_TEST_EVENT_TYPE_VALUES:
        return value
    raise TypeError(f"Unexpected value {value!r}. Expected one of {WEBHOOK_TEST_EVENT_TYPE_VALUES!r}")
