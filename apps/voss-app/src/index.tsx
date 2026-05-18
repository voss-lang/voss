import { render } from 'solid-js/web';
import { invoke } from '@tauri-apps/api/core';
import App from './App';
import { applyThemeOverrides } from './theme/applyTheme';
import './index.css';

const root = document.getElementById('root');
if (!root) throw new Error('No #root element');

// Apply theme overrides from settings.json before first render.
// invoke resolves fast (sync file read on Rust side); absent/malformed -> {}
// Silent fallback to baked Variant B per UI-SPEC Copywriting Contract.
invoke<Record<string, string>>('get_theme_overrides')
  .then((overrides) => {
    applyThemeOverrides(overrides);
  })
  .catch((e) => {
    console.error('[voss-app] theme override error:', e);
  })
  .finally(() => {
    render(() => <App />, root);
  });
