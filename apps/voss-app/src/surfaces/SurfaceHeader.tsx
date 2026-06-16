import { type Component, Show } from 'solid-js';
import Folder from 'lucide-solid/icons/folder';
import GitBranch from 'lucide-solid/icons/git-branch';
import Plus from 'lucide-solid/icons/plus';

export type SurfaceHeaderProps = {
  projectName: string;
  projectPath?: string | null;
  gitBranch?: string | null;
  onNewSession?: () => void;
  onNewTask?: () => void;
};

const ICON_PROPS = {
  size: 18,
  color: 'currentColor',
  'aria-hidden': true,
  strokeWidth: 1.75,
} as const;

/** Shorten absolute paths under `/Users/<user>/` to `~/…`; otherwise last segment. */
export function formatProjectPath(path: string | null | undefined): string | null {
  if (!path || path.trim().length === 0) return null;

  const homeMatch = path.match(/^\/Users\/[^/]+(\/.*)?$/);
  if (homeMatch) {
    const rest = homeMatch[1] ?? '';
    return rest.length > 0 ? `~${rest}` : '~';
  }

  const parts = path.split('/').filter(Boolean);
  if (parts.length === 0) return path;
  if (parts.length === 1) return parts[0]!;
  return `~/${parts.slice(-2).join('/')}`;
}

const SurfaceHeader: Component<SurfaceHeaderProps> = (props) => {
  const titleText = () =>
    props.projectName && props.projectName.length > 0
      ? props.projectName
      : 'Voss ADE';

  const displayPath = () => formatProjectPath(props.projectPath);
  const branch = () => props.gitBranch?.trim() || null;
  const showMeta = () => displayPath() !== null || branch() !== null;

  return (
    <header class="surface-header">
      <div class="surface-header__left">
        <div class="surface-header__icon-tile" aria-hidden="true">
          <Folder {...ICON_PROPS} />
        </div>
        <div class="surface-header__info">
          <h1 class="surface-header__title">{titleText()}</h1>
          <Show when={showMeta()}>
            <div class="surface-header__meta">
              <Show when={displayPath()}>
                <span class="surface-header__meta-path">{displayPath()}</span>
              </Show>
              <Show when={displayPath() && branch()}>
                <span class="surface-header__meta-sep" aria-hidden="true">
                  ·
                </span>
              </Show>
              <Show when={branch()}>
                <span class="surface-header__meta-branch">
                  <GitBranch size={12} color="currentColor" aria-hidden="true" strokeWidth={1.75} />
                  <span>{branch()}</span>
                </span>
              </Show>
            </div>
          </Show>
        </div>
      </div>
      <div class="surface-header__actions">
        <button
          type="button"
          class="surface-header__btn-secondary"
          onClick={() => props.onNewSession?.()}
        >
          New session
        </button>
        <button
          type="button"
          class="surface-header__btn-primary"
          onClick={() => props.onNewTask?.()}
        >
          <Plus size={14} color="currentColor" aria-hidden="true" strokeWidth={2} />
          New task
        </button>
      </div>
    </header>
  );
};

export default SurfaceHeader;
