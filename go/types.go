package tembuilder

import "github.com/tembuilderlabs/tembuilder-sdk/go/internal/api"

// Response and request types of the public API, generated from the OpenAPI
// contract. They are aliases, so values are interchangeable with the
// generated client's types.
type (
	Account               = api.Account
	Project               = api.Project
	Template              = api.Template
	TemplateDetail        = api.TemplateDetail
	TemplateInput         = api.TemplateInput
	TemplatePage          = api.TemplatePage
	TemplateVariant       = api.TemplateVariant
	TemplateVersion       = api.TemplateVersion
	RenderRequest         = api.RenderRequest
	RenderQueued          = api.RenderQueued
	RenderStatus          = api.RenderStatus
	Render                = api.Render
	RenderPage            = api.RenderPage
	RenderStatusEvent     = api.RenderStatusEvent
	RenderStatusEventData = api.RenderStatusEventData
	WebhookTestEvent      = api.WebhookTestEvent

	ListTemplatesParams       = api.ListTemplatesParams
	ListTemplatesParamsStatus = api.ListTemplatesParamsStatus
	GetTemplateParams         = api.GetTemplateParams
	ListRendersParams         = api.ListRendersParams
	ListRendersParamsStatus   = api.ListRendersParamsStatus
)

// Render statuses. "pending" is the only non-terminal status.
const (
	RenderStatusPending       = "pending"
	RenderStatusSuccess       = "success"
	RenderStatusFailed        = "failed"
	RenderStatusQuotaExceeded = "quota_exceeded"
)

// Ptr returns a pointer to v, for optional request fields.
func Ptr[T any](v T) *T { return &v }
