// Command voss-tui-go is the Go terminal client for `voss serve`.
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	tea "charm.land/bubbletea/v2"
	"github.com/charmbracelet/colorprofile"
	voss "github.com/vosslang/voss/sdk/go"
)

const usage = `usage: voss-tui-go [--attach URL --token TOKEN] [--cwd DIR] [--model MODEL] [command]

Without a command, opens a chat session.

commands:
  doctor     run the server's diagnostics and exit
  sessions   list saved sessions for --cwd and exit

Without --attach, voss serve is started from VOSS_BIN, else voss on PATH.
--token defaults to VOSS_TUI_TOKEN.
`

type options struct {
	attach string
	token  string
	cwd    string
	model  string
	cmd    string
}

// parseArgs accepts the flags before or after the command, like the Rust client.
func parseArgs(args []string) (options, error) {
	o := options{token: os.Getenv("VOSS_TUI_TOKEN")}
	fs := flag.NewFlagSet("voss-tui-go", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	fs.StringVar(&o.attach, "attach", "", "")
	fs.StringVar(&o.token, "token", o.token, "")
	fs.StringVar(&o.cwd, "cwd", ".", "")
	fs.StringVar(&o.model, "model", "", "")
	if err := fs.Parse(args); err != nil {
		return o, err
	}
	o.cmd = "chat"
	if fs.NArg() > 0 {
		o.cmd = fs.Arg(0)
		if err := fs.Parse(fs.Args()[1:]); err != nil {
			return o, err
		}
		if fs.NArg() > 0 {
			return o, fmt.Errorf("unexpected argument %q", fs.Arg(0))
		}
	}
	switch o.cmd {
	case "chat", "doctor", "sessions":
	default:
		return o, fmt.Errorf("unknown command %q", o.cmd)
	}
	abs, err := filepath.Abs(o.cwd)
	if err != nil {
		return o, err
	}
	o.cwd = abs
	return o, nil
}

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	code := run(ctx, os.Args[1:], os.Stdout, os.Stderr)
	stop()
	os.Exit(code)
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	o, err := parseArgs(args)
	if err != nil {
		fmt.Fprintf(stderr, "voss-tui-go: %v\n\n%s", err, usage)
		return 2
	}
	if o.cmd == "sessions" {
		printSessions(stdout, o.cwd, readSavedSessions(o.cwd))
		return 0
	}

	client, err := connect(ctx, o)
	if err != nil {
		return fail(ctx, stderr, err)
	}
	defer client.Close()

	if o.cmd == "chat" {
		if err := runChat(ctx, client, o); err != nil {
			return fail(ctx, stderr, err)
		}
		return 0
	}

	report, err := client.Doctor(ctx, o.cwd)
	if err != nil {
		return fail(ctx, stderr, fmt.Errorf("doctor: %w", err))
	}
	printDoctor(stdout, report)
	return report.ExitCode
}

// fail reports err, or exits quietly with 130 when the user interrupted.
func fail(ctx context.Context, stderr io.Writer, err error) int {
	if ctx.Err() != nil {
		return 130
	}
	fmt.Fprintf(stderr, "voss-tui-go: %v\n", err)
	return 1
}

func runChat(ctx context.Context, client *voss.Client, o options) error {
	s, err := client.OpenSession(ctx, voss.SessionOptions{Cwd: o.cwd, Model: o.model})
	if err != nil {
		return fmt.Errorf("create session: %w", err)
	}
	info, err := client.GetSession(ctx, s.Id)
	if err != nil {
		return fmt.Errorf("read session: %w", err)
	}
	// One stream for the session's life: the server aborts the turn when it drops.
	streamCtx, cancel := context.WithCancel(ctx)
	defer cancel()
	events, err := client.Events(streamCtx, s.Id)
	if err != nil {
		return fmt.Errorf("event stream: %w", err)
	}
	meta := sessionMeta{ID: s.Id, Cwd: o.cwd, Provider: providerLabel(s.Auth), Model: info.Model, Git: gitSummary(o.cwd)}
	opts := []tea.ProgramOption{tea.WithContext(ctx)}
	// Rich, which draws the Textual TUI, trusts COLORTERM even under tmux;
	// Bubble Tea's detection does not, so match Rich.
	if ct := os.Getenv("COLORTERM"); ct == "truecolor" || ct == "24bit" {
		opts = append(opts, tea.WithColorProfile(colorprofile.TrueColor))
	}
	_, err = tea.NewProgram(newChatModel(ctx, client, meta, events), opts...).Run()
	return err
}

func connect(ctx context.Context, o options) (*voss.Client, error) {
	if o.attach != "" {
		return voss.AttachClient(o.attach, o.token), nil
	}
	return voss.Spawn(ctx, voss.LaunchOptions{Cwd: o.cwd})
}

func printDoctor(w io.Writer, r voss.DoctorReport) {
	provider := "none"
	if r.HasProvider {
		provider = "resolved"
	}
	fmt.Fprintf(w, "  auth      : %s — %s\n", r.AuthSource, r.AuthDetail)
	fmt.Fprintf(w, "  provider  : %s\n", provider)
	fmt.Fprintf(w, "  model     : %s\n", r.DefaultModel)
	for _, c := range r.Checks {
		fmt.Fprintf(w, "  %s %-22s %s\n", statusGlyph(c.Status), c.Name, c.Detail)
		if c.Status != "OK" && c.Fix != "" {
			fmt.Fprintf(w, "       → %s\n", c.Fix)
		}
	}
}

func statusGlyph(status string) string {
	switch status {
	case "OK":
		return "✓"
	case "WARN":
		return "⚠"
	case "FAIL":
		return "✗"
	}
	return "?"
}
