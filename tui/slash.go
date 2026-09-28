package main

import (
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"

	tea "charm.land/bubbletea/v2"
	voss "github.com/vosslang/voss/sdk/go"
)

// Slash commands this client runs, with the names, help text and output of
// the CLI's registry (voss/harness/cli.py _build_slash_registry). Output a
// command prints goes into a "system" block and errors into a warning, as
// the Textual TUI does with the captured stdout and stderr.

type slashCommand struct {
	name, help string
	aliases    []string
}

var slashCommands = []slashCommand{
	{"/cost", "session cost so far ([--by-model | --by-tool])", nil},
	{"/diff", "show working-tree diff: /diff [--staged] [<path>]", nil},
	{"/doctor", "run health checks (diagnose-only; repairs via `voss doctor --fix`)", nil},
	{"/exit", "leave the REPL (also Ctrl-D)", []string{"/quit"}},
	{"/help", "show this list", nil},
	{"/mode", "plan | edit | auto; auto requires --confirm", nil},
}

// helpGroups follows _print_slash_help; commands in no group go under Other.
var helpGroups = []struct {
	header string
	names  []string
}{
	{"Editing", []string{"/diff", "/apply", "/discard"}},
	{"Session", []string{"/resume", "/budget", "/cost", "/clear", "/save-session"}},
	{"Insight", []string{"/why", "/probable", "/btrace", "/vdiff", "/tools", "/analyze"}},
	{"Control", []string{"/help", "/exit", "/mode", "/model"}},
}

func commandNames() []string {
	names := make([]string, len(slashCommands))
	for i, c := range slashCommands {
		names[i] = c.name
	}
	return names
}

func lookupCommand(name string) (slashCommand, bool) {
	for _, c := range slashCommands {
		if c.name == name || contains(c.aliases, name) {
			return c, true
		}
	}
	return slashCommand{}, false
}

func slashHelp(name string) string {
	c, _ := lookupCommand(name)
	return c.help
}

func helpText() string {
	var out []string
	placed := map[string]bool{}
	section := func(header string, cmds []slashCommand) {
		if len(cmds) == 0 {
			return
		}
		width := 0
		for _, c := range cmds {
			width = max(width, len(c.name))
		}
		out = append(out, header)
		for _, c := range cmds {
			out = append(out, "  "+padRight(c.name, width)+"  "+c.help)
		}
		out = append(out, "")
	}
	for _, g := range helpGroups {
		var cmds []slashCommand
		for _, n := range g.names {
			if c, ok := lookupCommand(n); ok && c.name == n {
				cmds = append(cmds, c)
				placed[n] = true
			}
		}
		section(g.header, cmds)
	}
	var other []slashCommand
	for _, c := range slashCommands {
		if !placed[c.name] {
			other = append(other, c)
		}
	}
	section("Other", other)
	return strings.TrimRight(strings.Join(out, "\n"), "\n")
}

type slashOutputMsg struct{ stdout, stderr string }

// output turns a command's printed text into blocks, as Textual does.
func output(stdout, stderr string) []block {
	var out []block
	if s := strings.TrimRight(stdout, " \t\n"); s != "" {
		out = append(out, roleBlock("system", s))
	}
	if s := strings.TrimRight(stderr, " \t\n"); s != "" {
		out = append(out, roleBlock("warning", glyphs.Warn+" "+s))
	}
	return out
}

func (m *chatModel) slash(text string) tea.Cmd {
	args, err := shlexSplit(text)
	if err != nil {
		m.add(roleBlock("warning", glyphs.Warn+" invalid slash command: "+err.Error()))
		return nil
	}
	cmd, ok := lookupCommand(args[0])
	if !ok {
		m.add(roleBlock("warning", glyphs.Warn+" unknown command: "+text+". /help for list."))
		return nil
	}
	args = args[1:]
	switch cmd.name {
	case "/exit":
		m.quitting = true
		return tea.Quit
	case "/help":
		m.add(output(helpText(), "")...)
	case "/mode":
		m.add(output(m.setMode(args))...)
	case "/cost":
		return costCommand(m.ctx, m.client, m.sessionID, m.turn.model, args)
	case "/diff":
		return diffCommand(m.ctx, m.cwd, args)
	case "/doctor":
		return doctorCommand(m.ctx, m.client, m.cwd, args)
	}
	return nil
}

// setMode follows the CLI's /mode and returns what it prints.
func (m *chatModel) setMode(args []string) (string, string) {
	if len(args) == 0 {
		return "  mode: " + m.mode, ""
	}
	switch mode := args[0]; {
	case mode != "plan" && mode != "edit" && mode != "auto" && mode != "observe":
		return "", "mode must be plan|edit|auto|observe"
	case mode == "auto" && !contains(args, "--confirm"):
		return "", "escalating to auto requires --confirm (e.g. /mode auto --confirm)"
	default:
		m.mode = mode
		return "  mode: " + mode, ""
	}
}

func costCommand(ctx context.Context, client *voss.Client, id, model string, args []string) tea.Cmd {
	return func() tea.Msg {
		flags := map[string]bool{}
		for _, a := range args {
			flags[strings.TrimLeft(a, "-")] = true
		}
		if flags["by-tool"] {
			return slashOutputMsg{stdout: "  /cost --by-tool: per-tool cost tracking lands with T6 SLASH-07. " +
				"Recorder doesn't yet attribute provider cost to individual tool calls."}
		}
		c, err := client.Cost(ctx, id)
		if err != nil {
			return errMsg{"cost", err}
		}
		total := fmt.Sprintf("session cost: $%.4f", c.TotalUsd)
		if !flags["by-model"] {
			return slashOutputMsg{stdout: total}
		}
		if c.Turns == 0 {
			return slashOutputMsg{stdout: total + " (no runs yet)"}
		}
		return slashOutputMsg{stdout: total + "\n" + fmt.Sprintf("  %s  $%.4f", model, c.TotalUsd)}
	}
}

func diffCommand(ctx context.Context, cwd string, args []string) tea.Cmd {
	return func() tea.Msg {
		argv := []string{"diff"}
		if len(args) > 0 && (args[0] == "--staged" || args[0] == "--cached") {
			argv = append(argv, "--cached")
			args = args[1:]
		}
		argv = append(argv, args...)
		ctx, cancel := context.WithTimeout(ctx, 15*time.Second)
		defer cancel()
		c := exec.CommandContext(ctx, "git", argv...)
		c.Dir = cwd
		var stdout, stderr strings.Builder
		c.Stdout, c.Stderr = &stdout, &stderr
		err := c.Run()
		if err != nil && stderr.Len() == 0 {
			if _, exited := err.(*exec.ExitError); !exited {
				return slashOutputMsg{stderr: "/diff failed: " + err.Error()}
			}
		}
		if err != nil && stderr.Len() > 0 {
			return slashOutputMsg{stderr: stderr.String()}
		}
		body := strings.TrimRight(stdout.String(), " \t\n")
		if body == "" {
			body = "  (no changes)"
		}
		return slashOutputMsg{stdout: body}
	}
}

func doctorCommand(ctx context.Context, client *voss.Client, cwd string, args []string) tea.Cmd {
	return func() tea.Msg {
		if len(args) > 0 && (args[0] == "--help" || args[0] == "-h") {
			return slashOutputMsg{stdout: "usage: /doctor   run health checks (repairs: `voss doctor --fix` in shell)"}
		}
		report, err := client.Doctor(ctx, cwd)
		if err != nil {
			return errMsg{"doctor", err}
		}
		width := 0
		for _, c := range report.Checks {
			width = max(width, len(c.Name))
		}
		var lines []string
		for _, c := range report.Checks {
			lines = append(lines, fmt.Sprintf("  %s  %s %s", statusGlyph(c.Status), padRight(c.Name, width+2), c.Detail))
			if c.Fix != "" && c.Status != "OK" {
				lines = append(lines, "     → "+c.Fix)
			}
		}
		return slashOutputMsg{stdout: strings.Join(lines, "\n")}
	}
}
