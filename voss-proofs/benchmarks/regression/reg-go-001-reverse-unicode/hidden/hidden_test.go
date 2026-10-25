package strutil

import (
	"testing"
	"unicode/utf8"
)

func TestHiddenUnicode(t *testing.T) {
	cases := map[string]string{"héllo": "olléh", "日本語": "語本日", "a€b": "b€a"}
	for in, want := range cases {
		got := Reverse(in)
		if got != want || !utf8.ValidString(got) {
			t.Errorf("Reverse(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestHiddenASCII(t *testing.T) {
	if Reverse("") != "" || Reverse("ab") != "ba" {
		t.Fatal("ASCII behavior changed")
	}
}
