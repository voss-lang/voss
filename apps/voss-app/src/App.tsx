import Titlebar from './components/titlebar/Titlebar';

export default function App() {
  return (
    <div
      style={{
        display: 'flex',
        'flex-direction': 'column',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
      }}
    >
      <Titlebar />
      {/* Body — intentionally empty in A1. Grid and PTY panes land in A2/A3. */}
      <div style={{ flex: '1', background: 'var(--bg-0)' }} />
    </div>
  );
}
