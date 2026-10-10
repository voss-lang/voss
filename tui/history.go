package main

import (
	"encoding/json"
	"errors"
	"io"
	"os"
	"path/filepath"
)

func (m *chatModel) loadHistory(path string) error {
	f, err := os.Open(path)
	if errors.Is(err, os.ErrNotExist) {
		m.historyPath = path
		return nil
	}
	if err != nil {
		return err
	}
	defer f.Close()
	d := json.NewDecoder(f)
	for {
		var text string
		if err := d.Decode(&text); err != nil {
			if errors.Is(err, io.EOF) {
				m.historyPath = path
				return nil
			}
			return err
		}
		m.history = append(m.history, text)
	}
}

func (m *chatModel) rememberPrompt(text string) {
	m.history = append(m.history, text)
	if m.historyPath == "" {
		return
	}
	if err := appendHistory(m.historyPath, text); err != nil {
		m.add(roleBlock("warning", "prompt history: "+err.Error()))
	}
}

func appendHistory(path, text string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0o600)
	if err != nil {
		return err
	}
	err = json.NewEncoder(f).Encode(text)
	closeErr := f.Close()
	if err != nil {
		return err
	}
	return closeErr
}
