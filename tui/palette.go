package main

import (
	"io/fs"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	"charm.land/lipgloss/v2"
	"github.com/charmbracelet/x/ansi"
)

// The slash and @-mention palettes, from slash_palette.py and
// mention_palette.py: a rounded accent box above the input, at most eight
// rows tall, driven by the text being typed.

const (
	paletteMaxResults = 8
	paletteMaxLines   = 6 // Textual's max-height 8 includes the border
	mentionWalkLimit  = 4000
	paletteHighlight  = "#133752" // Textual's list cursor, measured from its output
)

type paletteKind int

const (
	paletteNone paletteKind = iota
	paletteSlash
	paletteMention
	paletteSession
)

type picker struct {
	kind   paletteKind
	names  []string // command names or file paths, ranked
	labels []string
	idx    int
}

// rankCommands orders command names like slash_palette.rank_commands:
// position of the query in the name, then name; no query means recent first.
func rankCommands(query string, names, recent []string) []string {
	if query == "" {
		var out []string
		for _, r := range recent {
			if contains(names, r) && !contains(out, r) {
				out = append(out, r)
			}
		}
		rest := make([]string, 0, len(names))
		for _, n := range names {
			if !contains(out, n) {
				rest = append(rest, n)
			}
		}
		sort.Strings(rest)
		out = append(out, rest...)
		return out[:min(len(out), paletteMaxResults)]
	}
	q := strings.TrimLeft(strings.ToLower(query), "/")
	type scored struct {
		idx  int
		name string
	}
	var hits []scored
	for _, n := range names {
		if i := strings.Index(strings.TrimLeft(strings.ToLower(n), "/"), q); i >= 0 {
			hits = append(hits, scored{i, n})
		}
	}
	sort.Slice(hits, func(a, b int) bool {
		if hits[a].idx != hits[b].idx {
			return hits[a].idx < hits[b].idx
		}
		return hits[a].name < hits[b].name
	})
	out := make([]string, 0, len(hits))
	for _, h := range hits[:min(len(hits), paletteMaxResults)] {
		out = append(out, h.name)
	}
	return out
}

var mentionIgnoreDirs = map[string]bool{
	".git": true, ".hg": true, ".svn": true, "node_modules": true, "target": true, "dist": true, "build": true,
	".venv": true, "venv": true, "__pycache__": true, ".mypy_cache": true, ".pytest_cache": true, ".ruff_cache": true,
	".voss": true, ".voss-cache": true, ".idea": true, ".vscode": true, ".cursor": true, ".next": true, ".turbo": true,
}

// gatherFiles lists files under root like mention_palette.gather_files,
// skipping dot and build directories and stopping at the walk limit.
func gatherFiles(root string) []string {
	var out []string
	_ = filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return nil
		}
		if d.IsDir() {
			if path != root && (mentionIgnoreDirs[d.Name()] || strings.HasPrefix(d.Name(), ".")) {
				return filepath.SkipDir
			}
			return nil
		}
		rel, _ := filepath.Rel(root, path)
		out = append(out, filepath.ToSlash(rel))
		if len(out) >= mentionWalkLimit {
			return fs.SkipAll
		}
		return nil
	})
	return out
}

// rankFiles orders paths like mention_palette.rank_files: basename matches
// first, then full-path matches, earlier position and shorter path winning.
func rankFiles(query string, paths []string) []string {
	if query == "" {
		sorted := append([]string(nil), paths...)
		sort.SliceStable(sorted, func(a, b int) bool {
			da, db := strings.Count(sorted[a], "/"), strings.Count(sorted[b], "/")
			if da != db {
				return da < db
			}
			return strings.ToLower(sorted[a]) < strings.ToLower(sorted[b])
		})
		return sorted[:min(len(sorted), paletteMaxResults)]
	}
	q := strings.ToLower(query)
	type scored struct {
		tier, pos, length int
		path              string
	}
	var hits []scored
	for _, p := range paths {
		low := strings.ToLower(p)
		base := low[strings.LastIndex(low, "/")+1:]
		if b := strings.Index(base, q); b >= 0 {
			hits = append(hits, scored{0, b, len(p), p})
		} else if f := strings.Index(low, q); f >= 0 {
			hits = append(hits, scored{1, f, len(p), p})
		}
	}
	sort.Slice(hits, func(a, b int) bool {
		x, y := hits[a], hits[b]
		if x.tier != y.tier {
			return x.tier < y.tier
		}
		if x.pos != y.pos {
			return x.pos < y.pos
		}
		if x.length != y.length {
			return x.length < y.length
		}
		return x.path < y.path
	})
	out := make([]string, 0, paletteMaxResults)
	for _, h := range hits[:min(len(hits), paletteMaxResults)] {
		out = append(out, h.path)
	}
	return out
}

// findMentionToken returns the rune index of the @ in the word ending at
// cursor and the query after it, like mention_palette.find_mention_token.
func findMentionToken(text []rune, cursor int) (int, string, bool) {
	if cursor < 0 || cursor > len(text) {
		return 0, "", false
	}
	for i := cursor - 1; i >= 0 && !unicode.IsSpace(text[i]); i-- {
		if text[i] == '@' {
			return i, string(text[i+1 : cursor]), true
		}
	}
	return 0, "", false
}

// cursorOffset is the editor cursor as a rune offset into its value.
func (m chatModel) cursorOffset() int {
	lines := strings.Split(m.editor.Value(), "\n")
	offset := m.editor.Line() + m.editor.Column()
	for _, l := range lines[:min(m.editor.Line(), len(lines))] {
		offset += len([]rune(l))
	}
	return offset
}

// syncPalette opens, updates or closes a palette after the text changes.
func (m *chatModel) syncPalette() {
	text := m.editor.Value()
	prev := m.pal
	switch {
	case m.search.active || m.paletteDismissed:
		m.pal = picker{}
	case prev.kind == paletteSession:
		m.pal = picker{kind: paletteSession}
		query := strings.ToLower(strings.TrimSpace(text))
		for _, s := range m.savedSessions {
			if s.Id == m.sessionID || !strings.Contains(strings.ToLower(s.Id+" "+s.Name), query) {
				continue
			}
			m.pal.names = append(m.pal.names, s.Id)
			m.pal.labels = append(m.pal.labels, s.Id+"  "+s.Name+"  "+s.UpdatedAt)
		}
	case strings.HasPrefix(text, "/"):
		names := rankCommands(text, commandNames(), m.recentCommands)
		m.pal = picker{kind: paletteSlash, names: names}
		for _, n := range names {
			m.pal.labels = append(m.pal.labels, padRight(n, 16)+" "+slashHelp(n))
		}
	default:
		_, query, ok := findMentionToken([]rune(text), m.cursorOffset())
		if !ok {
			m.pal, m.mentionFiles = picker{}, nil
			return
		}
		if m.mentionFiles == nil {
			m.mentionFiles = gatherFiles(m.cwd)
		}
		names := rankFiles(query, m.mentionFiles)
		m.pal = picker{kind: paletteMention, names: names, labels: names}
	}
	// Keep the highlighted entry when it is still listed, as Textual does.
	if prev.kind == m.pal.kind && prev.idx < len(prev.names) {
		for i, n := range m.pal.names {
			if n == prev.names[prev.idx] {
				m.pal.idx = i
			}
		}
	}
}

func padRight(s string, n int) string {
	return s + strings.Repeat(" ", max(n-len([]rune(s)), 0))
}

func contains(list []string, s string) bool {
	for _, x := range list {
		if x == s {
			return true
		}
	}
	return false
}

// paletteBox draws the palette as a rounded accent box of the given width.
func paletteBox(p picker, width int) string {
	bg := palette.Surface
	empty := "no matching commands"
	if p.kind == paletteSession {
		bg, empty = palette.Raised, "no saved sessions match (Esc to close)"
	}
	if p.kind == paletteMention {
		bg, empty = palette.Raised, "no matching files"
	}
	inner := max(width-2, 1)
	type row struct {
		text string
		item int
	}
	var rows []row
	for i, label := range p.labels {
		for _, w := range richWrap(label, inner) {
			rows = append(rows, row{w, i})
		}
	}
	if len(rows) == 0 {
		rows = []row{{empty, -1}}
	}
	start := 0
	for i, r := range rows {
		if r.item == p.idx {
			last := i
			for last+1 < len(rows) && rows[last+1].item == p.idx {
				last++
			}
			start = max(0, last-paletteMaxLines+1)
			break
		}
	}
	rows = rows[start:min(len(rows), start+paletteMaxLines)]
	lines := make([]string, len(rows))
	for i, r := range rows {
		st := lipgloss.NewStyle().Foreground(col(screenText)).Background(col(bg))
		if r.item == p.idx && len(p.names) > 0 {
			st = st.Background(col(paletteHighlight))
		}
		lines[i] = st.Render(r.text + strings.Repeat(" ", max(inner-ansi.StringWidth(r.text), 0)))
	}
	return lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(col(palette.Accent)).
		BorderBackground(col(palette.Surface)).
		Render(strings.Join(lines, "\n"))
}
