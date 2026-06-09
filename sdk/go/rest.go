package voss

import (
	"context"
	"net/http"
	"net/url"
)

// SessionInfo is a live session (GET /session, GET /session/:id).
type SessionInfo struct {
	Id    string `json:"id"`
	Cwd   string `json:"cwd"`
	Model string `json:"model"`
	Title string `json:"title"`
	Busy  bool   `json:"busy"`
}

// SavedSession is a persisted session (GET /sessions/saved).
type SavedSession struct {
	Id           string  `json:"id"`
	Name         string  `json:"name"`
	Cwd          string  `json:"cwd"`
	Model        string  `json:"model"`
	UpdatedAt    string  `json:"updated_at"`
	TotalCostUsd float64 `json:"total_cost_usd"`
	Turns        int     `json:"turns"`
}

// CostInfo is the cost rollup (GET /session/:id/cost).
type CostInfo struct {
	TotalUsd float64 `json:"total_usd"`
	Turns    int     `json:"turns"`
}

// DoctorCheck is one diagnostic row from GET /doctor.
type DoctorCheck struct {
	Name   string `json:"name"`
	Status string `json:"status"`
	Detail string `json:"detail"`
	Fix    string `json:"fix"`
}

// DoctorReport is the GET /doctor response.
type DoctorReport struct {
	AuthSource   string        `json:"auth_source"`
	AuthDetail   string        `json:"auth_detail"`
	HasProvider  bool          `json:"has_provider"`
	DefaultModel string        `json:"default_model"`
	ExitCode     int           `json:"exit_code"`
	Checks       []DoctorCheck `json:"checks"`
}

// CreateSession opens a session rooted at cwd. POST /session -> 201.
func (c *Client) CreateSession(ctx context.Context, cwd string) (string, error) {
	body := CreateSessionBody{Cwd: &cwd}
	var out struct {
		Id string `json:"id"`
	}
	if err := c.sendJSON(ctx, http.MethodPost, "/session", body, &out, http.StatusCreated); err != nil {
		return "", err
	}
	return out.Id, nil
}

// ListSessions returns the active in-memory sessions. GET /session -> 200.
func (c *Client) ListSessions(ctx context.Context) ([]SessionInfo, error) {
	var out struct {
		Sessions []SessionInfo `json:"sessions"`
	}
	if err := c.getJSON(ctx, "/session", http.StatusOK, &out); err != nil {
		return nil, err
	}
	return out.Sessions, nil
}

// ListSavedSessions returns persisted sessions for cwd. GET /sessions/saved -> 200.
func (c *Client) ListSavedSessions(ctx context.Context, cwd string) ([]SavedSession, error) {
	path := "/sessions/saved?" + url.Values{"cwd": {cwd}}.Encode()
	var out struct {
		Sessions []SavedSession `json:"sessions"`
	}
	if err := c.getJSON(ctx, path, http.StatusOK, &out); err != nil {
		return nil, err
	}
	return out.Sessions, nil
}

// GetSession returns a single active session. GET /session/:id -> 200.
func (c *Client) GetSession(ctx context.Context, id string) (SessionInfo, error) {
	var out SessionInfo
	if err := c.getJSON(ctx, "/session/"+url.PathEscape(id), http.StatusOK, &out); err != nil {
		return SessionInfo{}, err
	}
	return out, nil
}

// DeleteSession removes a session. DELETE /session/:id -> 204 No Content.
func (c *Client) DeleteSession(ctx context.Context, id string) error {
	return c.sendJSON(ctx, http.MethodDelete, "/session/"+url.PathEscape(id), nil, nil, http.StatusNoContent)
}

// PostMessage submits a user turn (mode "" = server default). POST -> 202; 409 if a turn is running.
func (c *Client) PostMessage(ctx context.Context, id, text, mode string) error {
	partType := "text"
	body := MessageBody{
		Parts: &[]MessagePart{{Type: &partType, Text: &text}},
	}
	if mode != "" {
		body.Mode = &mode
	}
	return c.sendJSON(ctx, http.MethodPost, "/session/"+url.PathEscape(id)+"/message", body, nil, http.StatusAccepted)
}

// Abort requests cancellation of the running turn. POST /session/:id/abort -> 202.
func (c *Client) Abort(ctx context.Context, id string) error {
	return c.sendJSON(ctx, http.MethodPost, "/session/"+url.PathEscape(id)+"/abort", nil, nil, http.StatusAccepted)
}

// Cost returns the session cost rollup. GET /session/:id/cost -> 200.
func (c *Client) Cost(ctx context.Context, id string) (CostInfo, error) {
	var out CostInfo
	if err := c.getJSON(ctx, "/session/"+url.PathEscape(id)+"/cost", http.StatusOK, &out); err != nil {
		return CostInfo{}, err
	}
	return out, nil
}

// Doctor returns the server's environment/provider diagnostics. GET /doctor -> 200.
func (c *Client) Doctor(ctx context.Context) (DoctorReport, error) {
	path := "/doctor?" + url.Values{"auth": {"auto"}, "cwd": {"."}}.Encode()
	var out DoctorReport
	if err := c.getJSON(ctx, path, http.StatusOK, &out); err != nil {
		return DoctorReport{}, err
	}
	return out, nil
}

// PermissionReply answers a pending gate. choice: "a"/"A"/"d"/"y"/"n" (PROTOCOL
// §7). POST -> 200. stale=true means already resolved (not an error); 401/404
// surface as *VossError.
func (c *Client) PermissionReply(ctx context.Context, sessionID, id, choice string) (bool, error) {
	body := PermissionReply{Id: id, Choice: choice}
	var out struct {
		Status string `json:"status"`
	}
	if err := c.sendJSON(ctx, http.MethodPost, "/session/"+url.PathEscape(sessionID)+"/permission", body, &out, http.StatusOK); err != nil {
		return false, err
	}
	return out.Status == "stale", nil
}
