//go:build tools

// Package tools pins the oapi-codegen generator as a module dependency so
// types.gen.go can be regenerated deterministically.
//
// The go.mod `tool` directive is the primary pin; this build-tagged blank
// import is the portable fallback for tooling that does not honor it. The go
// directive is 1.24 because oapi-codegen v2.7.1 and runtime v1.4.1 both
// require it.
package tools

import _ "github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen"
