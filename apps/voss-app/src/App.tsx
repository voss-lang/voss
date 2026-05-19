import Titlebar from './components/titlebar/Titlebar';
import PaneComponent from './pane/PaneComponent';

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
      {/* A2: single PTY pane fills the body. A3 turns this into a grid. */}
      <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
        <PaneComponent index={1} />
      </div>
    </div>
  );
}
