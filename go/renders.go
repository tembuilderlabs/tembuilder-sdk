package tembuilder

import (
	"context"
	"io"
	"iter"
	"mime"
	"net/http"
	"time"

	"github.com/tembuilderlabs/tembuilder-sdk/go/internal/api"
)

// RendersService queues renders, follows their status and downloads PDFs.
type RendersService struct {
	api   *api.Client
	files *http.Client
}

// fileURLExpiryMargin skips a signed file URL this close to expiry.
const fileURLExpiryMargin = 30 * time.Second

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

// DownloadFrom fetches the PDF of a successful render from the status
// returned by Get, WaitFor or CreateAndWait. It downloads straight from
// storage through the signed FileUrl, without sending the API key; when that
// link is missing, about to expire or refused, it falls back to Download.
func (s *RendersService) DownloadFrom(ctx context.Context, status *RenderStatus) (*RenderFile, error) {
	if url, ok := usableFileURL(status); ok {
		if file := s.downloadSigned(ctx, url); file != nil {
			return file, nil
		}
	}
	return s.Download(ctx, status.RenderId.String())
}

func usableFileURL(status *RenderStatus) (string, bool) {
	if status.FileUrl == nil || *status.FileUrl == "" {
		return "", false
	}
	if status.FileUrlExpiresAt != nil && time.Until(*status.FileUrlExpiresAt) <= fileURLExpiryMargin {
		return "", false
	}
	return *status.FileUrl, true
}

// downloadSigned fetches a signed file URL; nil means "use the API endpoint".
func (s *RendersService) downloadSigned(ctx context.Context, url string) *RenderFile {
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return nil
	}
	request.Header.Set("User-Agent", "tembuilder-go/"+Version)
	response, err := s.files.Do(request)
	if err != nil {
		return nil // unreachable storage, after the transport's retries
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode > 299 {
		return nil
	}
	content, err := io.ReadAll(response.Body)
	if err != nil {
		return nil
	}
	return renderFile(content, response.Header)
}

func renderFile(content []byte, header http.Header) *RenderFile {
	contentType := header.Get("Content-Type")
	if contentType == "" {
		contentType = "application/pdf"
	}
	return &RenderFile{Content: content, ContentType: contentType, Filename: filenameFromDisposition(header)}
}

// Download fetches the PDF of a successful render by id through
// GET /v1/renders/{id}/download. Prefer DownloadFrom when you have the
// render's status: it skips passing the file through the API.
func (s *RendersService) Download(ctx context.Context, renderID string) (*RenderFile, error) {
	response, err := s.api.DownloadRender(ctx, renderID)
	parsed, err := call(response, err, api.ParseDownloadRenderResponse)
	if err != nil {
		return nil, err
	}
	return renderFile(parsed.Body, parsed.HTTPResponse.Header), nil
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
