package voss

import (
	"context"
	"net/http"
	"net/url"
)

func (c *Client) ListCommands(ctx context.Context) (CommandCatalog, error) {
	var out CommandCatalog
	err := c.getJSON(ctx, "/commands", http.StatusOK, &out)
	return out, err
}

func (c *Client) ExecuteCommand(ctx context.Context, id, name string, args []string) (CommandResult, error) {
	var out CommandResult
	request := CommandRequest{Name: name}
	if len(args) > 0 {
		request.Args = &args
	}
	err := c.sendJSON(ctx, http.MethodPost, "/session/"+url.PathEscape(id)+"/command",
		request, &out, http.StatusOK)
	return out, err
}
