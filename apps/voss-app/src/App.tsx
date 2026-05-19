import Titlebar from './components/titlebar/Titlebar';
import GridRoot from './grid/GridRoot';

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
      {/* A3: the binary-split grid fills the body (leaves are A2 panes). */}
      <div style={{ flex: '1', 'min-height': '0', background: 'var(--bg-0)' }}>
        <GridRoot />
      </div>
    </div>
  );
}
