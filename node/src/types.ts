import type { components, operations } from './generated/schema.js'

type Schemas = components['schemas']

export type Account = Schemas['Account']
export type Project = Schemas['Project']
export type Template = Schemas['Template']
export type TemplateDetail = Schemas['TemplateDetail']
export type TemplateVersion = Schemas['TemplateVersion']
export type TemplateVariant = Schemas['TemplateVariant']
export type TemplateInput = Schemas['TemplateInput']
export type TemplatePage = Schemas['TemplatePage']
export type RenderRequest = Schemas['RenderRequest']
export type RenderQueued = Schemas['RenderQueued']
export type RenderStatus = Schemas['RenderStatus']
export type Render = Schemas['Render']
export type RenderPage = Schemas['RenderPage']
export type RenderStatusEvent = Schemas['RenderStatusEvent']
export type WebhookTestEvent = Schemas['WebhookTestEvent']
export type ErrorBody = Schemas['Error']

export type ListTemplatesParams = NonNullable<operations['listTemplates']['parameters']['query']>
export type GetTemplateParams = NonNullable<operations['getTemplate']['parameters']['query']>
export type ListRendersParams = NonNullable<operations['listRenders']['parameters']['query']>

/** Any event Tembuilder delivers to a webhook endpoint. */
export type WebhookEvent = RenderStatusEvent | WebhookTestEvent

/** Render statuses after which the status no longer changes. */
export const TERMINAL_RENDER_STATUSES = ['success', 'failed', 'quota_exceeded'] as const
