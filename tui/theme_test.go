package main

import (
	"os"
	"reflect"
	"regexp"
	"strconv"
	"strings"
	"testing"
	"unicode"
)

const textualDir = "../voss/harness/tui/"

// pyConstants reads `NAME = "value"` lines from a Python file.
func pyConstants(t *testing.T, file string) map[string]string {
	t.Helper()
	raw, err := os.ReadFile(textualDir + file)
	if err != nil {
		t.Fatal(err)
	}
	out := map[string]string{}
	for _, m := range regexp.MustCompile(`(?m)^([A-Z_]+) = ("(?:[^"\\]|\\.)*")`).FindAllStringSubmatch(string(raw), -1) {
		v, err := strconv.Unquote(m[2])
		if err != nil {
			t.Fatalf("%s: %s: %v", file, m[1], err)
		}
		out[m[1]] = v
	}
	return out
}

// pyDict reads the `"NAME": "value"` entries of NO_UNICODE_FALLBACK.
func pyDict(t *testing.T, file string) map[string]string {
	t.Helper()
	raw, err := os.ReadFile(textualDir + file)
	if err != nil {
		t.Fatal(err)
	}
	body := string(raw)
	body = body[strings.Index(body, "NO_UNICODE_FALLBACK"):]
	body = body[:strings.Index(body, "}")]
	out := map[string]string{}
	for _, m := range regexp.MustCompile(`"([A-Z_]+)": ("(?:[^"\\]|\\.)*")`).FindAllStringSubmatch(body, -1) {
		v, err := strconv.Unquote(m[2])
		if err != nil {
			t.Fatalf("%s: %s: %v", file, m[1], err)
		}
		out[m[1]] = v
	}
	return out
}

// fields maps a struct's CamelCase fields to Python's SNAKE_CASE names.
func fields(v any) map[string]string {
	out := map[string]string{}
	rv := reflect.ValueOf(v)
	for i := 0; i < rv.NumField(); i++ {
		var sb strings.Builder
		for j, r := range rv.Type().Field(i).Name {
			if j > 0 && unicode.IsUpper(r) {
				sb.WriteByte('_')
			}
			sb.WriteRune(unicode.ToUpper(r))
		}
		out[sb.String()] = rv.Field(i).String()
	}
	return out
}

func TestPaletteMatchesTextual(t *testing.T) {
	want := pyConstants(t, "palette.py")
	if got := fields(palette); !reflect.DeepEqual(got, want) {
		t.Fatalf("palette drifted from palette.py:\ngo: %v\npy: %v", got, want)
	}
}

func TestGlyphsMatchTextual(t *testing.T) {
	if got, want := fields(unicodeGlyphs), pyConstants(t, "glyphs.py"); !reflect.DeepEqual(got, want) {
		t.Fatalf("glyphs drifted from glyphs.py:\ngo: %v\npy: %v", got, want)
	}
	if got, want := fields(asciiGlyphs), pyDict(t, "glyphs.py"); !reflect.DeepEqual(got, want) {
		t.Fatalf("ASCII fallbacks drifted from NO_UNICODE_FALLBACK:\ngo: %v\npy: %v", got, want)
	}
}
