// Command specgen regenerates ../../types.gen.go from the committed OpenAPI
// snapshot. It is the target of the //go:generate directive in doc.go and the
// single deterministic entry point used by the drift gate.
//
// Why this exists: FastAPI emits OpenAPI 3.1.0, but oapi-codegen v2.7.1 only
// supports 3.0.x (https://github.com/oapi-codegen/oapi-codegen/issues/373) and
// fails on 3.1 null-union nullables (anyOf: [{type: X}, {type: null}]). specgen
// performs a minimal, deterministic 3.1->3.0 downgrade in memory — set the
// version to 3.0.3 and rewrite single-type null unions to `nullable: true` —
// then hands the normalized spec to oapi-codegen via the pinned `tool`
// directive. The upstream contracts/openapi.json (owned by V13.1) is never
// modified.
//
// Input resolution: ../../contracts/openapi.json when present (the live V13.1
// artifact), otherwise testdata/openapi.fixture.json (the captured pre-V13.1
// fallback). Paths are relative to sdk/go, the working directory `go generate`
// uses for doc.go.
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
)

const (
	contractsPath = "../../contracts/openapi.json"
	fixturePath   = "testdata/openapi.fixture.json"
	configPath    = "oapi-codegen.yaml"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, "specgen:", err)
		os.Exit(1)
	}
}

func run() error {
	in := contractsPath
	if _, err := os.Stat(in); err != nil {
		in = fixturePath
	}
	raw, err := os.ReadFile(in)
	if err != nil {
		return fmt.Errorf("read spec %s: %w", in, err)
	}
	var spec map[string]any
	if err := json.Unmarshal(raw, &spec); err != nil {
		return fmt.Errorf("parse spec %s: %w", in, err)
	}
	spec["openapi"] = "3.0.3"
	normalized := normalize(spec)

	out, err := json.MarshalIndent(normalized, "", "  ")
	if err != nil {
		return fmt.Errorf("marshal normalized spec: %w", err)
	}
	tmp, err := os.CreateTemp("", "voss-openapi-3.0-*.json")
	if err != nil {
		return fmt.Errorf("create temp spec: %w", err)
	}
	defer os.Remove(tmp.Name())
	if _, err := tmp.Write(out); err != nil {
		tmp.Close()
		return fmt.Errorf("write temp spec: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp spec: %w", err)
	}

	cmd := exec.Command("go", "tool", "oapi-codegen", "-config", configPath, tmp.Name())
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("oapi-codegen: %w", err)
	}
	fmt.Fprintf(os.Stderr, "specgen: generated types.gen.go from %s\n", in)
	return nil
}

// normalize recursively downgrades OpenAPI 3.1 null-union nullables to the 3.0
// `nullable: true` form. A schema node of the shape
//
//	{ "anyOf": [ {<schema>}, {"type": "null"} ] }
//
// (exactly one non-null subschema) is collapsed to <schema> with
// "nullable": true and any sibling keys preserved. All other nodes pass through
// unchanged. The transform is deterministic and order-independent.
func normalize(v any) any {
	switch t := v.(type) {
	case map[string]any:
		if anyOf, ok := t["anyOf"].([]any); ok {
			var nonNull []any
			hasNull := false
			for _, s := range anyOf {
				if sm, ok := s.(map[string]any); ok && sm["type"] == "null" {
					hasNull = true
					continue
				}
				nonNull = append(nonNull, s)
			}
			if hasNull && len(nonNull) == 1 {
				if base, ok := nonNull[0].(map[string]any); ok {
					merged := map[string]any{}
					for k, vv := range base {
						merged[k] = vv
					}
					merged["nullable"] = true
					for k, vv := range t {
						if k == "anyOf" {
							continue
						}
						if _, exists := merged[k]; !exists {
							merged[k] = vv
						}
					}
					return normalize(merged)
				}
			}
		}
		out := make(map[string]any, len(t))
		for k, vv := range t {
			out[k] = normalize(vv)
		}
		return out
	case []any:
		out := make([]any, len(t))
		for i, vv := range t {
			out[i] = normalize(vv)
		}
		return out
	default:
		return v
	}
}
