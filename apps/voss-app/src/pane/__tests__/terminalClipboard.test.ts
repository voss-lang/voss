import { describe, expect, it } from 'vitest';
import {
  clipboardImageFile,
  quotePathForShell,
  resolveTerminalCopyAction,
  shouldGuardTerminalPaste,
} from '../terminalClipboard';

describe('terminalClipboard', () => {
  it('Cmd+C copies only when a terminal selection exists by default', () => {
    expect(resolveTerminalCopyAction(true, 'smart')).toBe('copy-selection');
    expect(resolveTerminalCopyAction(false, 'smart')).toBe('noop');
  });

  it('keeps explicit interrupt mode available', () => {
    expect(resolveTerminalCopyAction(false, 'sigint')).toBe('interrupt');
    expect(resolveTerminalCopyAction(true, 'sigint')).toBe('interrupt');
  });

  it('guards multi-line paste unless bypassed', () => {
    expect(shouldGuardTerminalPaste('one line', false)).toBe(false);
    expect(shouldGuardTerminalPaste('one\ntwo', false)).toBe(true);
    expect(shouldGuardTerminalPaste('one\r\ntwo', false)).toBe(true);
    expect(shouldGuardTerminalPaste('one\ntwo', true)).toBe(false);
  });

  it('single-quotes pasted image paths for shell input', () => {
    expect(quotePathForShell('/tmp/Voss Paste/image.png')).toBe(
      "'/tmp/Voss Paste/image.png'",
    );
    expect(quotePathForShell("/tmp/ben's image.png")).toBe(
      "'/tmp/ben'\\''s image.png'",
    );
  });

  it('picks image files from clipboard data before non-image files', () => {
    const image = new File([new Uint8Array([1])], 'shot.png', {
      type: 'image/png',
    });
    const text = new File(['hi'], 'note.txt', { type: 'text/plain' });
    const data = {
      items: [
        {
          kind: 'file',
          type: 'text/plain',
          getAsFile: () => text,
        },
        {
          kind: 'file',
          type: 'image/png',
          getAsFile: () => image,
        },
      ],
      files: [],
    } as unknown as DataTransfer;

    expect(clipboardImageFile(data)).toBe(image);
  });
});
