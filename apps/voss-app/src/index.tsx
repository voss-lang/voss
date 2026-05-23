import { render } from 'solid-js/web';
import { invoke } from '@tauri-apps/api/core';
import App from './App';
import { applyThemeOverrides } from './theme/applyTheme';
import { applyThemeToRuntime, getCommittedTheme } from './themes/themeRuntime';
import './index.css';

const root = document.getElementById('root');
if (!root) throw new Error('No #root element');

// Apply default theme (Voss Ignite) CSS vars before first render.
// This overrides the baked variant-b.css fallback values with the warm palette.
applyThemeToRuntime(getCommittedTheme());

// Then apply any user-saved theme overrides from settings.json on top.
invoke<Record<string, string>>('get_theme_overrides')
  .then((overrides) => {
    if (Object.keys(overrides).length > 0) {
      applyThemeOverrides(overrides);
    }
  })
  .catch((e) => {
    console.error('[voss-app] theme override error:', e);
  })
  .finally(() => {
    render(() => <App />, root);
  });
