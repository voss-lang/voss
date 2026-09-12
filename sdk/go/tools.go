//go:build tools

// Package tools pins the oapi-codegen generator as a module dependency so
// types.gen.go can be regenerated deterministically.
package tools

import _ "github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen"
