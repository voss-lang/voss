package main

import "os"

// palette mirrors voss/harness/tui/palette.py; theme_test.go fails on any drift.
var palette = struct {
	Accent, Dim, Good, Warn, Error, Bg, Surface, Raised, Text string
}{
	Accent:  "#ff5b1f",
	Dim:     "#888888",
	Good:    "#5FD75F",
	Warn:    "#FFD75F",
	Error:   "#FF5F5F",
	Bg:      "#121212",
	Surface: "#1c1c1c",
	Raised:  "#262626",
	Text:    "#dadada",
}

// glyphSet mirrors voss/harness/tui/glyphs.py. Field names are the Python
// constant names in CamelCase.
type glyphSet struct {
	Prompt, UserInput, ToolCall, Warn, BarFill, BarEmpty, BudgetFill, BudgetEmpty,
	NestLast, NestMid, Fork, Assistant, Working, SpinnerFrames, ToolOk, OutputElbow,
	ChevronClosed, ChevronOpen, Approx, Check string
}

var unicodeGlyphs = glyphSet{
	Prompt:        "▌",
	UserInput:     "❯",
	ToolCall:      "⏵",
	Warn:          "⚠",
	BarFill:       "█",
	BarEmpty:      "░",
	BudgetFill:    "▰",
	BudgetEmpty:   "▱",
	NestLast:      "└─",
	NestMid:       "├─",
	Fork:          "⎇",
	Assistant:     "●",
	Working:       "✦",
	SpinnerFrames: "⠋⠙⠹⠸⠼⠴⠦⠧",
	ToolOk:        "⏺",
	OutputElbow:   "⎿",
	ChevronClosed: "▸",
	ChevronOpen:   "▾",
	Approx:        "≈",
	Check:         "✓",
}

var asciiGlyphs = glyphSet{
	Prompt:        "|",
	UserInput:     ">",
	ToolCall:      ">",
	Warn:          "!",
	BarFill:       "#",
	BarEmpty:      ".",
	BudgetFill:    "=",
	BudgetEmpty:   "-",
	NestLast:      "+-",
	NestMid:       "+-",
	Fork:          "+",
	Assistant:     "*",
	Working:       "*",
	SpinnerFrames: `|/-\`,
	ToolOk:        "*",
	OutputElbow:   "|_",
	ChevronClosed: ">",
	ChevronOpen:   "v",
	Approx:        "~",
	Check:         "*",
}

// glyphs follows the Textual rule: VOSS_NO_UNICODE=1 switches every glyph to ASCII.
var glyphs = func() glyphSet {
	if os.Getenv("VOSS_NO_UNICODE") == "1" {
		return asciiGlyphs
	}
	return unicodeGlyphs
}()
