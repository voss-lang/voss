import { createSignal, onMount, Show } from 'solid-js';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { platform } from '@tauri-apps/plugin-os';

// macOS traffic-light colors — hardcoded per OS convention (NOT token vars).
// Sole exception to the "no raw hex in components" rule.
// Source: A1-UI-SPEC.md "macOS Traffic-Light Colors" table.
const TRAFFIC_CLOSE    = '#ff5f57';
const TRAFFIC_MINIMIZE = '#febc2e';
const TRAFFIC_ZOOM     = '#28c840';

function MacTrafficLights() {
  const win = getCurrentWindow();
  const [isFullscreen, setIsFullscreen] = createSignal(false);

  onMount(async () => {
    try {
      setIsFullscreen(await win.isFullscreen());
    } catch {
      setIsFullscreen(false);
    }
  });

  const handleZoom = async () => {
    const next = !isFullscreen();
    setIsFullscreen(next);
    await win.setFullscreen(next);
  };

  const circle = (bg: string) => ({
    width: '12px',
    height: '12px',
    'border-radius': '50%',
    background: bg,
    border: 'none',
    cursor: 'pointer',
    padding: '0',
  });

  return (
    <div
      style={{
        display: 'flex',
        gap: '6px',
        'align-items': 'center',
        'padding-left': '12px',
        'flex-shrink': '0',
      }}
    >
      <button title="close" onClick={() => win.close()} style={circle(TRAFFIC_CLOSE)} />
      <button title="minimize" onClick={() => win.minimize()} style={circle(TRAFFIC_MINIMIZE)} />
      <button title="zoom" onClick={handleZoom} style={circle(TRAFFIC_ZOOM)} />
    </div>
  );
}

// linux/win placeholder — null. Replaced in A10 soak / CI matrix (CONTEXT D-04).
function StubControls() {
  return null;
}

export default function WindowControls() {
  const [os, setOs] = createSignal<string>('');
  onMount(async () => {
    try {
      setOs(await platform());
    } catch {
      setOs('unknown');
    }
  });

  return (
    <Show when={os() === 'macos'} fallback={<StubControls />}>
      <MacTrafficLights />
    </Show>
  );
}
