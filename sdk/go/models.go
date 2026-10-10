package voss

import (
	"context"
	"net/http"
	"net/url"
)

// ModelSelection identifies a model and its credential route. An auth-only
// selection keeps a compatible model or chooses that route's default.
type ModelSelection struct {
	Model    string `json:"model,omitempty"`
	Auth     string `json:"auth,omitempty"`
	Provider string `json:"provider,omitempty"`
}

func (c *Client) ListModels(ctx context.Context) (ModelCatalog, error) {
	var out ModelCatalog
	err := c.getJSON(ctx, "/models", http.StatusOK, &out)
	return out, err
}

func (c *Client) SelectModel(ctx context.Context, id string, selection ModelSelection) (SessionInfo, error) {
	var out SessionInfo
	err := c.sendJSON(ctx, http.MethodPost, "/session/"+url.PathEscape(id)+"/model", selection, &out, http.StatusOK)
	return out, err
}
