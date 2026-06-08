//go:build tools

// Package tools pins the oapi-codegen code generator as a module dependency so
// the generated types.gen.go can be regenerated deterministically.
//
// The module's go directive is 1.24 (forced: oapi-codegen v2.7.1 and
// oapi-codegen/runtime v1.4.1 both declare `go 1.24`). The original V13.3-01
// plan targeted a go 1.22 floor, but that is not achievable with the locked,
// security-audited generator/runtime versions. The Go 1.24 `tool` directive in
// go.mod is the primary pin; this build-tagged blank import is the portable
// fallback for tooling that does not honor the tool directive.
package tools

import _ "github.com/oapi-codegen/oapi-codegen/v2/cmd/oapi-codegen"
