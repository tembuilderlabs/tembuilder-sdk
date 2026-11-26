package tembuilder

import (
	"context"
	"iter"

	"github.com/tembuilderlabs/tembuilder-sdk/go/internal/api"
)

// TemplatesService discovers templates and their render input.
type TemplatesService struct{ api *api.Client }

// List returns one page of templates, most recently updated first.
func (s *TemplatesService) List(ctx context.Context, params ListTemplatesParams) (*TemplatePage, error) {
	response, err := s.api.ListTemplates(ctx, &params)
	parsed, err := call(response, err, api.ParseListTemplatesResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON200, parsed.StatusCode())
}

// All iterates every template across pages; params.Page is ignored.
func (s *TemplatesService) All(ctx context.Context, params ListTemplatesParams) iter.Seq2[Template, error] {
	return paginate(func(page int32) ([]Template, bool, error) {
		params.Page = &page
		result, err := s.List(ctx, params)
		if err != nil {
			return nil, false, err
		}
		return result.Data, result.HasMore, nil
	})
}

// Get returns a template (by UUID or slug) with its versions and the input
// contract of one version (params.Version, default the current version).
func (s *TemplatesService) Get(ctx context.Context, templateID string, params GetTemplateParams) (*TemplateDetail, error) {
	response, err := s.api.GetTemplate(ctx, templateID, &params)
	parsed, err := call(response, err, api.ParseGetTemplateResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON200, parsed.StatusCode())
}

// paginate yields items page by page until a page reports no more results
// or an error, which is yielded once.
func paginate[T any](fetch func(page int32) ([]T, bool, error)) iter.Seq2[T, error] {
	return func(yield func(T, error) bool) {
		for page := int32(1); ; page++ {
			items, more, err := fetch(page)
			if err != nil {
				var zero T
				yield(zero, err)
				return
			}
			for _, item := range items {
				if !yield(item, nil) {
					return
				}
			}
			if !more {
				return
			}
		}
	}
}
