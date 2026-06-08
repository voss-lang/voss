package voss

import (
	"go/parser"
	"go/token"
	"io/fs"
	"path/filepath"
	"strings"
	"testing"
)

// TestNoFFI enforces the thin-client boundary (SPEC req 7 / VSDK-GO-07): the Go
// SDK introduces no cgo and reimplements/imports no orchestration. It parses
// every .go file under sdk/go and fails on:
//   - import "C" (cgo)
//   - any import path under voss/harness or voss_runtime (orchestration)
//
// Allowed imports: the Go stdlib, github.com/oapi-codegen/runtime, and the
// local module github.com/vosslang/voss/sdk/go/...
func TestNoFFI(t *testing.T) {
	fset := token.NewFileSet()
	err := filepath.WalkDir(".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if d.Name() == "testdata" {
				return filepath.SkipDir
			}
			return nil
		}
		if !strings.HasSuffix(path, ".go") {
			return nil
		}
		f, perr := parser.ParseFile(fset, path, nil, parser.ImportsOnly)
		if perr != nil {
			t.Fatalf("parse %s: %v", path, perr)
		}
		for _, imp := range f.Imports {
			p := strings.Trim(imp.Path.Value, `"`)
			if p == "C" {
				t.Errorf("%s uses cgo (import \"C\") — forbidden in the thin client", path)
			}
			if strings.Contains(p, "voss/harness") || strings.Contains(p, "voss_runtime") {
				t.Errorf("%s imports orchestration package %q — forbidden (no reimpl/import)", path, p)
			}
		}
		return nil
	})
	if err != nil {
		t.Fatalf("walk: %v", err)
	}
}
