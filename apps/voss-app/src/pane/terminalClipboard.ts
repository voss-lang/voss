export type CopyMode = 'smart' | 'copy' | 'sigint';

export type TerminalCopyAction = 'copy-selection' | 'interrupt' | 'noop';

export function resolveTerminalCopyAction(
  hasSelection: boolean,
  mode: CopyMode,
): TerminalCopyAction {
  if (mode === 'sigint') return 'interrupt';
  if (hasSelection) return 'copy-selection';
  return 'noop';
}

export function shouldGuardTerminalPaste(text: string, bypass: boolean): boolean {
  return !bypass && /[\r\n]/.test(text);
}

export function quotePathForShell(path: string): string {
  return `'${path.replaceAll("'", "'\\''")}'`;
}

export function clipboardImageFile(data: DataTransfer | null): File | null {
  if (!data) return null;

  for (const item of Array.from(data.items ?? [])) {
    if (item.kind !== 'file' || !item.type.startsWith('image/')) continue;
    const file = item.getAsFile();
    if (file) return file;
  }

  for (const file of Array.from(data.files ?? [])) {
    if (file.type.startsWith('image/')) return file;
  }

  return null;
}

export async function imageFileToBytes(file: File): Promise<{
  bytes: number[];
  mimeType: string;
}> {
  const buf = await file.arrayBuffer();
  return {
    bytes: Array.from(new Uint8Array(buf)),
    mimeType: file.type || 'image/png',
  };
}
