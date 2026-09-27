package main

import (
	"regexp"
	"slices"
	"strconv"
	"strings"

	"charm.land/lipgloss/v2"
	"github.com/alecthomas/chroma/v2"
	"github.com/alecthomas/chroma/v2/lexers"
	"github.com/charmbracelet/x/ansi"
	"github.com/yuin/goldmark"
	gast "github.com/yuin/goldmark/ast"
	"github.com/yuin/goldmark/extension"
	east "github.com/yuin/goldmark/extension/ast"
	gtext "github.com/yuin/goldmark/text"
	"github.com/yuin/goldmark/util"
)

// This file renders markdown the way rich.markdown.Markdown does inside the
// Textual TUI (code_theme="monokai"). Layout rules follow rich/markdown.py;
// named colours are Textual's MONOKAI terminal theme (textual/_ansi_theme.py).

const (
	ansiBlack        = "#1a1a1a"
	ansiMagenta      = "#f4005f"
	ansiCyan         = "#58d1eb"
	ansiBlue         = "#9d65ff"
	ansiBrightYellow = "#e0d561"
	monokaiBg        = "#272822"
	monokaiText      = "#f8f8f2"
)

// pygmentsMonokai is Pygments' monokai style, which Rich's Syntax uses.
var pygmentsMonokai = chroma.MustNewStyle("pygments-monokai", chroma.StyleEntries{
	chroma.Background:          "#f8f8f2 bg:#272822",
	chroma.Error:               "#ed007e bg:#1e0010",
	chroma.Comment:             "#959077",
	chroma.Keyword:             "#66d9ef",
	chroma.KeywordNamespace:    "#ff4689",
	chroma.Operator:            "#ff4689",
	chroma.Punctuation:         "#f8f8f2",
	chroma.Name:                "#f8f8f2",
	chroma.NameAttribute:       "#a6e22e",
	chroma.NameClass:           "#a6e22e",
	chroma.NameConstant:        "#66d9ef",
	chroma.NameDecorator:       "#a6e22e",
	chroma.NameException:       "#a6e22e",
	chroma.NameFunction:        "#a6e22e",
	chroma.NameOther:           "#a6e22e",
	chroma.NameTag:             "#ff4689",
	chroma.LiteralNumber:       "#ae81ff",
	chroma.Literal:             "#ae81ff",
	chroma.LiteralDate:         "#e6db74",
	chroma.LiteralString:       "#e6db74",
	chroma.LiteralStringEscape: "#ae81ff",
	chroma.GenericDeleted:      "#ff4689",
	chroma.GenericEmph:         "italic",
	chroma.GenericInserted:     "#a6e22e",
	chroma.GenericOutput:       "#66d9ef",
	chroma.GenericPrompt:       "bold #ff4689",
	chroma.GenericStrong:       "bold",
	chroma.GenericSubheading:   "#959077",
})

type mdStyle struct {
	fg, bg, link                           string
	bold, italic, underline, strike, faint bool
}

// with layers o over s, like Rich's Style addition.
func (s mdStyle) with(o mdStyle) mdStyle {
	if o.fg != "" {
		s.fg = o.fg
	}
	if o.bg != "" {
		s.bg = o.bg
	}
	if o.link != "" {
		s.link = o.link
	}
	s.bold = s.bold || o.bold
	s.italic = s.italic || o.italic
	s.underline = s.underline || o.underline
	s.strike = s.strike || o.strike
	s.faint = s.faint || o.faint
	return s
}

func (s mdStyle) render(text string) string {
	st := lipgloss.NewStyle()
	if s.fg != "" {
		st = st.Foreground(col(s.fg))
	}
	if s.bg != "" {
		st = st.Background(col(s.bg))
	}
	if s.link != "" {
		st = st.Hyperlink(s.link)
	}
	return st.Bold(s.bold).Italic(s.italic).Underline(s.underline).Strikethrough(s.strike).Faint(s.faint).Render(text)
}

var mdStyles = map[string]mdStyle{
	"h1":       {bold: true, underline: true},
	"h2":       {fg: ansiMagenta, underline: true},
	"h3":       {fg: ansiMagenta, bold: true},
	"h4":       {fg: ansiMagenta, italic: true},
	"h5":       {italic: true},
	"h6":       {faint: true},
	"em":       {italic: true},
	"strong":   {bold: true},
	"code":     {bold: true, fg: ansiCyan, bg: ansiBlack},
	"s":        {strike: true},
	"quote":    {fg: ansiMagenta},
	"bullet":   {bold: true},
	"number":   {fg: ansiCyan},
	"hr":       {faint: true},
	"link":     {fg: ansiBlue, underline: true},
	"kbd":      {bold: true, fg: ansiBrightYellow},
	"tableBox": {fg: ansiCyan},
}

// mdText is styled text; a line of output is an mdText with no newlines.
type span struct {
	text string
	st   mdStyle
}

type mdText []span

func (t mdText) plain() string {
	var sb strings.Builder
	for _, s := range t {
		sb.WriteString(s.text)
	}
	return sb.String()
}

func (t mdText) String() string {
	var sb strings.Builder
	for _, s := range t {
		if s.text != "" {
			sb.WriteString(s.st.render(s.text))
		}
	}
	return sb.String()
}

// slice cuts runes [from, to) out of t, keeping styles.
func (t mdText) slice(from, to int) mdText {
	var out mdText
	pos := 0
	for _, s := range t {
		r := []rune(s.text)
		lo, hi := max(from-pos, 0), min(to-pos, len(r))
		if lo < hi {
			out = append(out, span{string(r[lo:hi]), s.st})
		}
		pos += len(r)
	}
	return out
}

func (t mdText) width() int { return ansi.StringWidth(t.plain()) }

var richWords = regexp.MustCompile(`\s*\S+\s*`)

// divideLine returns the rune offsets at which Rich's divide_line breaks
// text to fit width, folding words wider than the line.
func divideLine(plain string, width int) []int {
	var breaks []int
	offset := 0
	runeAt := func(byteIdx int) int { return len([]rune(plain[:byteIdx])) }
	for _, loc := range richWords.FindAllStringIndex(plain, -1) {
		start, word := runeAt(loc[0]), plain[loc[0]:loc[1]]
		wordLen := ansi.StringWidth(strings.TrimRight(word, " \t\n"))
		if width-offset >= wordLen {
			offset += ansi.StringWidth(word)
			continue
		}
		if wordLen > width {
			chunks := chopCells(word, width)
			for i, chunk := range chunks {
				if start > 0 {
					breaks = append(breaks, start)
				}
				if i == len(chunks)-1 {
					offset = ansi.StringWidth(chunk)
				} else {
					start += len([]rune(chunk))
				}
			}
			continue
		}
		breaks = append(breaks, start)
		offset = ansi.StringWidth(word)
	}
	return breaks
}

func chopCells(s string, width int) []string {
	var out []string
	var cur strings.Builder
	w := 0
	for _, r := range s {
		rw := ansi.StringWidth(string(r))
		if w+rw > width && cur.Len() > 0 {
			out = append(out, cur.String())
			cur.Reset()
			w = 0
		}
		cur.WriteRune(r)
		w += rw
	}
	return append(out, cur.String())
}

// wrap splits t into lines like Rich's Text.wrap: hard lines first, then
// divideLine within each.
func (t mdText) wrap(width int) []mdText {
	var lines []mdText
	pos := 0
	for _, hard := range strings.Split(t.plain(), "\n") {
		n := len([]rune(hard))
		line := t.slice(pos, pos+n)
		pos += n + 1
		prev := 0
		for _, b := range append(divideLine(hard, max(width, 1)), n) {
			lines = append(lines, line.slice(prev, b))
			prev = b
		}
	}
	return lines
}

func pad(n int) mdText {
	if n <= 0 {
		return nil
	}
	return mdText{{strings.Repeat(" ", n), mdStyle{}}}
}

// richMarkdown renders src at width as Rich would.
func richMarkdown(src string, width int) string {
	md := goldmark.New(goldmark.WithExtensions(extension.Strikethrough, extension.Table))
	source := []byte(src)
	doc := md.Parser().Parse(gtext.NewReader(source))
	r := &mdRenderer{src: source}
	var out []string
	newLine := false
	for n := doc.FirstChild(); n != nil; n = n.NextSibling() {
		lines, ok := r.block(n, width, mdStyle{})
		if !ok {
			continue
		}
		// Rich renders lists, quotes and tables when they close, after their
		// children set the blank-line flag, so they always get a blank line.
		if newLine || isContainer(n) {
			out = append(out, "")
		}
		for _, l := range lines {
			out = append(out, l.String())
		}
		_, hr := n.(*gast.ThematicBreak)
		newLine = !hr
	}
	return strings.Join(out, "\n")
}

func isContainer(n gast.Node) bool {
	switch n.(type) {
	case *gast.List, *gast.Blockquote, *east.Table:
		return true
	}
	return false
}

type mdRenderer struct{ src []byte }

// children renders a container's blocks one after another with no blank
// lines, like Rich's Renderables.
func (r *mdRenderer) children(n gast.Node, width int, st mdStyle) []mdText {
	var out []mdText
	for c := n.FirstChild(); c != nil; c = c.NextSibling() {
		lines, _ := r.block(c, width, st)
		out = append(out, lines...)
	}
	return out
}

func (r *mdRenderer) block(n gast.Node, width int, st mdStyle) ([]mdText, bool) {
	switch n := n.(type) {
	case *gast.Paragraph, *gast.TextBlock:
		return r.inline(n, st).wrap(width), true
	case *gast.Heading:
		tag := "h" + strconv.Itoa(min(n.Level, 6))
		lines := r.inline(n, st.with(mdStyles[tag])).wrap(width)
		if tag == "h1" {
			for i, l := range lines {
				l = trimRight(l)
				excess := width - l.width()
				lines[i] = append(append(pad(excess/2), l...), pad(excess-excess/2)...)
			}
		}
		return lines, true
	case *gast.FencedCodeBlock:
		lang := ""
		if n.Info != nil {
			lang, _, _ = strings.Cut(string(n.Info.Segment.Value(r.src)), " ")
		}
		return codeBlock(r.lines(n), lang, width), true
	case *gast.CodeBlock:
		return codeBlock(r.lines(n), "", width), true
	case *gast.Blockquote:
		quote := st.with(mdStyles["quote"])
		var out []mdText
		for _, l := range r.children(n, width-4, quote) {
			out = append(out, append(mdText{{"▌ ", quote}}, l...))
		}
		return out, true
	case *gast.ThematicBreak:
		return []mdText{{{strings.Repeat("-", width), mdStyles["hr"]}}, nil}, true
	case *gast.List:
		return r.list(n, width, st), true
	case *east.Table:
		return r.table(n, width, st), true
	}
	return nil, false
}

func (r *mdRenderer) lines(n gast.Node) string {
	var sb strings.Builder
	for i := 0; i < n.Lines().Len(); i++ {
		seg := n.Lines().At(i)
		sb.Write(seg.Value(r.src))
	}
	return sb.String()
}

func (r *mdRenderer) list(n *gast.List, width int, st mdStyle) []mdText {
	var items []gast.Node
	for c := n.FirstChild(); c != nil; c = c.NextSibling() {
		items = append(items, c)
	}
	var out []mdText
	if !n.IsOrdered() {
		bullet := mdStyles["bullet"]
		for _, item := range items {
			for i, l := range r.children(item, width-3, st) {
				lead := mdText{{"   ", bullet}}
				if i == 0 {
					lead = mdText{{" • ", bullet}}
				}
				out = append(out, append(lead, l...))
			}
		}
		return out
	}
	start := n.Start
	numberWidth := len(strconv.Itoa(start+len(items))) + 2
	number := mdStyles["number"]
	for k, item := range items {
		numeral := strconv.Itoa(start + k)
		numeral = strings.Repeat(" ", max(numberWidth-1-len(numeral), 0)) + numeral + " "
		for i, l := range r.children(item, width-numberWidth, st) {
			lead := mdText{{strings.Repeat(" ", numberWidth), number}}
			if i == 0 {
				lead = mdText{{numeral, number}}
			}
			out = append(out, append(lead, l...))
		}
	}
	return out
}

// table draws Rich's box.SIMPLE table with show_edge, pad_edge=False and
// collapsed padding: space edges, two columns between cells, a rule under
// the header and cyan borders.
func (r *mdRenderer) table(n *east.Table, width int, st mdStyle) []mdText {
	var rows [][]mdText
	header := -1
	for row := n.FirstChild(); row != nil; row = row.NextSibling() {
		if _, ok := row.(*east.TableHeader); ok {
			header = len(rows)
		}
		var cells []mdText
		for cell := row.FirstChild(); cell != nil; cell = cell.NextSibling() {
			cellStyle := st
			if header == len(rows) {
				cellStyle = st.with(mdStyle{fg: ansiCyan})
			}
			cells = append(cells, r.inline(cell, cellStyle))
		}
		rows = append(rows, cells)
	}
	cols := len(n.Alignments)
	widths := make([]int, cols)
	for _, row := range rows {
		for i, c := range row {
			if i < cols {
				widths[i] = max(widths[i], c.width())
			}
		}
	}
	for total := sum(widths) + 2*(cols-1) + 2; total > width && slices.Max(widths) > 1; total-- {
		widest := 0
		for i := range widths {
			if widths[i] > widths[widest] {
				widest = i
			}
		}
		widths[widest]--
	}
	inner := sum(widths) + 2*(cols-1)
	box := mdStyles["tableBox"]
	edge := mdText{{strings.Repeat(" ", inner+2), box}}
	out := []mdText{edge}
	for ri, row := range rows {
		wrapped := make([][]mdText, cols)
		height := 1
		for i := range cols {
			if i < len(row) {
				wrapped[i] = row[i].wrap(widths[i])
			}
			height = max(height, len(wrapped[i]))
		}
		for h := range height {
			line := mdText{{" ", box}}
			for i := range cols {
				if i > 0 {
					line = append(line, span{"  ", box})
				}
				var cell mdText
				row := h
				if ri == header {
					// Rich aligns header cells to the bottom of the row.
					row = h - (height - len(wrapped[i]))
				}
				if row >= 0 && row < len(wrapped[i]) {
					cell = trimRight(wrapped[i][row])
				}
				gap := widths[i] - cell.width()
				switch n.Alignments[i] {
				case east.AlignRight:
					line = append(append(line, pad(gap)...), cell...)
				case east.AlignCenter:
					line = append(append(append(line, pad(gap/2)...), cell...), pad(gap-gap/2)...)
				default:
					line = append(append(line, cell...), pad(gap)...)
				}
			}
			out = append(out, append(line, span{" ", box}))
		}
		if ri == header {
			out = append(out, mdText{{" " + strings.Repeat("─", inner) + " ", box}})
		}
	}
	return append(out, edge)
}

func sum(xs []int) int {
	t := 0
	for _, x := range xs {
		t += x
	}
	return t
}

func trimRight(t mdText) mdText {
	for len(t) > 0 {
		last := t[len(t)-1]
		trimmed := strings.TrimRight(last.text, " ")
		if trimmed != "" {
			t[len(t)-1].text = trimmed
			return t
		}
		t = t[:len(t)-1]
	}
	return t
}

// inline flattens a block's inline children into styled text.
func (r *mdRenderer) inline(n gast.Node, st mdStyle) mdText {
	var out mdText
	var kbd []mdStyle
	var walk func(n gast.Node, st mdStyle)
	walk = func(n gast.Node, st mdStyle) {
		for c := n.FirstChild(); c != nil; c = c.NextSibling() {
			switch c := c.(type) {
			case *gast.Text:
				v := c.Segment.Value(r.src)
				if !c.IsRaw() {
					v = util.ResolveEntityNames(util.ResolveNumericReferences(util.UnescapePunctuations(v)))
				}
				out = append(out, span{string(v), st})
				if c.HardLineBreak() {
					out = append(out, span{"\n", st})
				} else if c.SoftLineBreak() {
					out = append(out, span{" ", st})
				}
			case *gast.String:
				out = append(out, span{string(c.Value), st})
			case *gast.Emphasis:
				tag := "em"
				if c.Level == 2 {
					tag = "strong"
				}
				walk(c, st.with(mdStyles[tag]))
			case *gast.CodeSpan:
				var sb strings.Builder
				for t := c.FirstChild(); t != nil; t = t.NextSibling() {
					if txt, ok := t.(*gast.Text); ok {
						sb.Write(txt.Segment.Value(r.src))
					}
				}
				out = append(out, span{sb.String(), st.with(mdStyles["code"])})
			case *east.Strikethrough:
				walk(c, st.with(mdStyles["s"]))
			case *gast.Link:
				walk(c, st.with(mdStyles["link"]).with(mdStyle{link: string(c.Destination)}))
			case *gast.AutoLink:
				url := string(c.URL(r.src))
				out = append(out, span{url, st.with(mdStyles["link"]).with(mdStyle{link: url})})
			case *gast.Image:
				before := len(out)
				walk(c, st)
				title := out[before:].plain()
				out = out[:before]
				if title == "" {
					dest := strings.Trim(string(c.Destination), "/")
					title = dest[strings.LastIndex(dest, "/")+1:]
				}
				out = append(out, span{"🌆 " + title + " ", st})
			case *gast.RawHTML:
				var sb strings.Builder
				for i := 0; i < c.Segments.Len(); i++ {
					seg := c.Segments.At(i)
					sb.Write(seg.Value(r.src))
				}
				switch sb.String() {
				case "<kbd>":
					kbd = append(kbd, st)
					st = st.with(mdStyles["kbd"])
				case "</kbd>":
					if len(kbd) > 0 {
						st, kbd = kbd[len(kbd)-1], kbd[:len(kbd)-1]
					}
				}
			default:
				walk(c, st)
			}
		}
	}
	walk(n, st)
	return out
}

// codeBlock draws Rich's Syntax(code, lexer, theme="monokai",
// word_wrap=True, padding=1) across the full width.
func codeBlock(code, lang string, width int) []mdText {
	code = strings.TrimRight(strings.ReplaceAll(code, "\t", "    "), " \t\n")
	bg := mdStyle{bg: monokaiBg}
	var lexer chroma.Lexer
	if lang != "" {
		lexer = lexers.Get(lang)
	}
	var highlighted mdText
	if lexer == nil {
		highlighted = mdText{{code, mdStyle{fg: monokaiText, bg: monokaiBg}}}
	} else if it, err := chroma.Coalesce(lexer).Tokenise(nil, code); err != nil {
		highlighted = mdText{{code, mdStyle{fg: monokaiText, bg: monokaiBg}}}
	} else {
		for _, tok := range it.Tokens() {
			e := pygmentsMonokai.Get(tok.Type)
			s := mdStyle{bg: monokaiBg, fg: monokaiText}
			if e.Colour.IsSet() {
				s.fg = e.Colour.String()
			}
			s.bold = e.Bold == chroma.Yes
			s.italic = e.Italic == chroma.Yes
			highlighted = append(highlighted, span{tok.Value, s})
		}
	}
	blank := mdText{{strings.Repeat(" ", width), bg}}
	out := []mdText{blank}
	for _, l := range highlighted.wrap(width - 2) {
		l = trimTrailingNewline(l)
		out = append(out, append(append(mdText{{" ", bg}}, l...), span{strings.Repeat(" ", max(width-1-l.width(), 0)), bg}))
	}
	return append(out, blank)
}

func trimTrailingNewline(t mdText) mdText {
	for i := range t {
		t[i].text = strings.ReplaceAll(t[i].text, "\n", "")
	}
	return t
}
