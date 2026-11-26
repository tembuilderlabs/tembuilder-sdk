package tembuilder

import (
	"context"
	"iter"
	"mime"
	"net/http"
	"time"

	"github.com/tembuilderlabs/tembuilder-sdk/go/internal/api"
)

// RendersService queues renders, follows their status and downloads PDFs.
type RendersService struct{ api *api.Client }

// RenderFile is a downloaded render output.
type RenderFile struct {
	Content     []byte
	ContentType string
	// Filename suggested by Content-Disposition; empty when absent.
	Filename string
}

// WaitOptions tunes WaitFor. Zero values use the defaults.
type WaitOptions struct {
	// PollInterval between status checks. Default 1s.
	PollInterval time.Duration
	// Timeout is the overall deadline. Default 2m.
	Timeout time.Duration
	// NotFoundGrace is how long a 404 counts as "job row not written yet"
	// after queueing. Default 15s.
	NotFoundGrace time.Duration
}

// Create queues a render. It returns the queued job, not the PDF.
func (s *RendersService) Create(ctx context.Context, request RenderRequest) (*RenderQueued, error) {
	response, err := s.api.CreateRender(ctx, request)
	parsed, err := call(response, err, api.ParseCreateRenderResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON202, parsed.StatusCode())
}

// Get returns the current status of a render.
func (s *RendersService) Get(ctx context.Context, renderID string) (*RenderStatus, error) {
	response, err := s.api.GetRender(ctx, renderID)
	parsed, err := call(response, err, api.ParseGetRenderResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON200, parsed.StatusCode())
}

// List returns one page of the render log, newest first.
func (s *RendersService) List(ctx context.Context, params ListRendersParams) (*RenderPage, error) {
	response, err := s.api.ListRenders(ctx, &params)
	parsed, err := call(response, err, api.ParseListRendersResponse)
	if err != nil {
		return nil, err
	}
	return required(parsed.JSON200, parsed.StatusCode())
}

// All iterates every render across pages; params.Page is ignored.
func (s *RendersService) All(ctx context.Context, params ListRendersParams) iter.Seq2[Render, error] {
	return paginate(func(page int32) ([]Render, bool, error) {
		params.Page = &page
		result, err := s.List(ctx, params)
		if err != nil {
			return nil, false, err
		}
		return result.Data, result.HasMore, nil
	})
}

// Download fetches the PDF of a successful render.
func (s *RendersService) Download(ctx context.Context, renderID string) (*RenderFile, error) {
	response, err := s.api.DownloadRender(ctx, renderID)
	parsed, err := call(response, err, api.ParseDownloadRenderResponse)
	if err != nil {
		return nil, err
	}
	contentType := parsed.HTTPResponse.Header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/pdf"
	}
	return &RenderFile{
		Content:     parsed.Body,
		ContentType: contentType,
		Filename:    filenameFromDisposition(parsed.HTTPResponse.Header),
	}, nil
}

// WaitFor polls a render until it is terminal. It returns the status on
// success, *RenderFailedError on "failed"/"quota_exceeded" and
// *RenderTimeoutError when the deadline passes.
func (s *RendersService) WaitFor(ctx context.Context, renderID string, options WaitOptions) (*RenderStatus, error) {
	interval := orDefault(options.PollInterval, time.Second)
	started := time.Now()
	deadline := started.Add(orDefault(options.Timeout, 2*time.Minute))
	notFoundUntil := started.Add(orDefault(options.NotFoundGrace, 15*time.Second))
	var last *RenderStatus
	for {
		status, err := s.Get(ctx, renderID)
		switch {
		case err == nil:
			last = status
			switch status.Status {
			case RenderStatusSuccess:
				return status, nil
			case RenderStatusFailed, RenderStatusQuotaExceeded:
				return nil, &RenderFailedError{Render: *status}
			}
		case IsNotFound(err) && last == nil && time.Now().Before(notFoundUntil):
			// The job row is written asynchronously right after queueing.
		default:
			return nil, err
		}
		remaining := time.Until(deadline)
		if remaining <= 0 {
			return nil, &RenderTimeoutError{RenderID: renderID, LastStatus: last}
		}
		timer := time.NewTimer(min(interval, remaining))
		select {
		case <-ctx.Done():
			timer.Stop()
			return nil, ctx.Err()
		case <-timer.C:
		}
	}
}

// CreateAndWait queues a render and waits for it to finish (see WaitFor).
func (s *RendersService) CreateAndWait(ctx context.Context, request RenderRequest, options WaitOptions) (*RenderStatus, error) {
	queued, err := s.Create(ctx, request)
	if err != nil {
		return nil, err
	}
	return s.WaitFor(ctx, queued.RenderId.String(), options)
}

func orDefault(value, fallback time.Duration) time.Duration {
	if value > 0 {
		return value
	}
	return fallback
}

// filenameFromDisposition reads filename / filename* from Content-Disposition.
func filenameFromDisposition(header http.Header) string {
	_, params, err := mime.ParseMediaType(header.Get("Content-Disposition"))
	if err != nil {
		return ""
	}
	return params["filename"]
}
