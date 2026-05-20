import { For, Show } from 'solid-js';
import {
  OPEN_PROJECT_LABEL,
  RECENTS_HEADING,
  START_PROJECT_LESS_LABEL,
} from '../../project/projectStorage';

export type SetupWindowProps = {
  recents: string[];
  onOpenProject: () => void;
  onOpenRecent: (path: string) => void;
  onStartProjectLess: () => void;
};

function basename(path: string) {
  return path.split('/').pop() || path;
}

export default function SetupWindow(props: SetupWindowProps) {
  return (
    <main
      aria-label="Project setup"
      style={{
        display: 'flex',
        'align-items': 'center',
        'justify-content': 'center',
        'min-height': '100%',
        padding: '32px',
        background: 'var(--bg-0)',
        color: 'var(--fg-0)',
        'font-family': 'var(--font-sans)',
      }}
    >
      <section
        style={{
          display: 'flex',
          'flex-direction': 'column',
          gap: '18px',
          width: 'min(560px, 100%)',
          padding: '24px',
          background: 'var(--bg-3)',
          border: '1px solid var(--border)',
        }}
      >
        <header
          style={{
            display: 'flex',
            'flex-direction': 'column',
            gap: '8px',
          }}
        >
          <h1
            style={{
              margin: '0',
              color: 'var(--fg-0)',
              'font-size': '20px',
              'font-weight': '600',
              'line-height': '1.2',
            }}
          >
            Choose a project
          </h1>
          <p
            style={{
              margin: '0',
              color: 'var(--fg-2)',
              'font-size': '13px',
              'line-height': '1.5',
            }}
          >
            Open a folder or continue without one.
          </p>
        </header>

        <div
          style={{
            display: 'flex',
            gap: '10px',
            'flex-wrap': 'wrap',
          }}
        >
          <button
            type="button"
            aria-label={OPEN_PROJECT_LABEL}
            onClick={props.onOpenProject}
            style={{
              background: 'var(--focus)',
              color: 'var(--fg-0)',
              border: '1px solid var(--focus)',
              padding: '9px 14px',
              'font-family': 'var(--font-mono)',
              'font-size': '12px',
              cursor: 'pointer',
              'line-height': '1',
            }}
          >
            {OPEN_PROJECT_LABEL}
          </button>
          <button
            type="button"
            aria-label={START_PROJECT_LESS_LABEL}
            onClick={props.onStartProjectLess}
            style={{
              background: 'transparent',
              color: 'var(--fg-2)',
              border: '1px solid var(--border)',
              padding: '9px 14px',
              'font-family': 'var(--font-mono)',
              'font-size': '12px',
              cursor: 'pointer',
              'line-height': '1',
            }}
          >
            {START_PROJECT_LESS_LABEL}
          </button>
        </div>

        <Show when={props.recents.length > 0}>
          <section
            aria-label={RECENTS_HEADING}
            style={{
              display: 'flex',
              'flex-direction': 'column',
              gap: '8px',
              'border-top': '1px solid var(--border)',
              'padding-top': '16px',
            }}
          >
            <h2
              style={{
                margin: '0',
                color: 'var(--fg-2)',
                'font-size': '12px',
                'font-weight': '500',
                'line-height': '1',
              }}
            >
              {RECENTS_HEADING}
            </h2>
            <div
              style={{
                display: 'flex',
                'flex-direction': 'column',
                gap: '6px',
              }}
            >
              <For each={props.recents}>
                {(path) => (
                  <button
                    type="button"
                    aria-label={`Open recent: ${basename(path)}`}
                    title={path}
                    onClick={() => props.onOpenRecent(path)}
                    style={{
                      background: 'var(--bg-0)',
                      color: 'var(--fg-0)',
                      border: '1px solid var(--border)',
                      padding: '8px 10px',
                      'font-family': 'var(--font-mono)',
                      'font-size': '12px',
                      cursor: 'pointer',
                      'line-height': '1.3',
                      'text-align': 'left',
                    }}
                  >
                    {path}
                  </button>
                )}
              </For>
            </div>
          </section>
        </Show>
      </section>
    </main>
  );
}
