// Command voss-tui-go is the Go terminal client for `voss serve`.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	voss "github.com/vosslang/voss/sdk/go"
)

const usage = `usage: voss-tui-go [--attach URL --token TOKEN] [--cwd DIR] <command>

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
	if err := fs.Parse(args); err != nil {
		return o, err
	}
	if fs.NArg() == 0 {
		return o, errors.New("missing command")
	}
	o.cmd = fs.Arg(0)
	if err := fs.Parse(fs.Args()[1:]); err != nil {
		return o, err
	}
	if fs.NArg() > 0 {
		return o, fmt.Errorf("unexpected argument %q", fs.Arg(0))
	}
	switch o.cmd {
	case "doctor", "sessions":
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
