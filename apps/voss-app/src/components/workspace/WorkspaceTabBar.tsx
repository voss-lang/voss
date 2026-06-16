import {
  For,
  Show,
  createSignal,
  onCleanup,
  onMount,
} from 'solid-js';
import type {
  WorkspaceCloseGuard,
  WorkspaceRecord,
} from '../../workspaces/workspaceStore';
import './workspace.css';

/** UI-SPEC copy constants — Copywriting Contract. */
export const COPY_NEW_WORKSPACE = 'New workspace';
export const COPY_RENAME_WORKSPACE = 'Rename workspace';
export const COPY_COLOR = 'Color';
export const COPY_CLOSE_WORKSPACE = 'Close workspace';
export const COPY_LAST_WORKSPACE_BLOCKED = 'Last workspace stays open';
export const COPY_CLOSE_RUNNING_CONFIRM =
  'Processes are running. Close workspace?';

/** UI-SPEC dimension contract. */
/** Matches pane header row (--pane-header-height). */
export const WORKSPACE_BAR_HEIGHT_PX = 22;
export const WORKSPACE_TAB_HEIGHT_PX = 22;
export const WORKSPACE_TAB_MIN_WIDTH_PX = 96;
export const WORKSPACE_TAB_MAX_WIDTH_PX = 220;
export const WORKSPACE_LEFT_INSET_PX = 12;

/** Fixed Warp-style eight-color palette (D-03). */
export const WORKSPACE_ACCENT_COLORS = [
  'neutral',
  'red',
  'orange',
  'green',
  'yellow',
  'cyan',
  'blue',
  'purple',
] as const;

export type WorkspaceAccentColor = (typeof WORKSPACE_ACCENT_COLORS)[number];

export type WorkspaceTabBarProps = {
  class?: string;
  workspaces: readonly WorkspaceRecord[];
  activeId: string | null;
  onActivate: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, name: string) => void;
  onColor: (id: string, color: string) => void;
  onClose: (id: string) => void;
  onReorder: (fromIndex: number, toIndex: number) => void;
  closeGuardFor: (id: string) => WorkspaceCloseGuard;
  hasRunningProcesses?: (id: string) => boolean;
  onCloseBlocked?: () => void;
  onCloseConfirm?: (id: string) => void;
};

type MenuView = 'main' | 'color' | 'confirm-close';

export function workspaceAccentVar(color: string): string {
  return `var(--workspace-${color}, var(--workspace-blue))`;
}

export default function WorkspaceTabBar(props: WorkspaceTabBarProps) {
  const [menu, setMenu] = createSignal<{
    id: string;
    x: number;
    y: number;
    view: MenuView;
  } | null>(null);
  const [renamingId, setRenamingId] = createSignal<string | null>(null);
  const [blockedCopy, setBlockedCopy] = createSignal<string | null>(null);
  let menuRoot: HTMLDivElement | undefined;

  const dismissMenu = () => setMenu(null);

  const openMenu = (id: string, anchor: HTMLElement, view: MenuView = 'main') => {
    const rect = anchor.getBoundingClientRect();
    setMenu({ id, x: rect.left, y: rect.bottom, view });
    setBlockedCopy(null);
  };

  let blockedTimer: ReturnType<typeof setTimeout> | undefined;
  const showBlocked = (msg: string) => {
    if (blockedTimer != null) clearTimeout(blockedTimer);
    setBlockedCopy(msg);
    blockedTimer = setTimeout(() => setBlockedCopy(null), 3000);
  };

  const requestClose = (id: string) => {
    const guard = props.closeGuardFor(id);
    if (!guard.canClose || guard.isLastWorkspace) {
      showBlocked(COPY_LAST_WORKSPACE_BLOCKED);
      props.onCloseBlocked?.();
      return;
    }
    if (props.hasRunningProcesses?.(id)) {
      const existing = menu();
      if (existing && existing.id === id) {
        setMenu({ ...existing, view: 'confirm-close' });
      } else {
        const tabEl = document.querySelector(
          `[data-workspace-tab="${id}"]`,
        ) as HTMLElement | null;
        if (tabEl) openMenu(id, tabEl, 'confirm-close');
      }
      return;
    }
    dismissMenu();
    props.onClose(id);
  };

  const confirmClose = (id: string) => {
    dismissMenu();
    if (props.onCloseConfirm) {
      props.onCloseConfirm(id);
    } else {
      props.onClose(id);
    }
  };

  const startRename = (id: string, anchor: HTMLElement) => {
    setRenamingId(id);
    dismissMenu();
    queueMicrotask(() => {
      const input = anchor.querySelector(
        '[data-workspace-rename-input]',
      ) as HTMLInputElement | null;
      input?.focus();
      input?.select();
    });
  };

  const commitRename = (id: string, value: string) => {
    setRenamingId(null);
    const trimmed = value.trim();
    if (trimmed.length > 0) props.onRename(id, trimmed);
  };

  const onDocKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      if (menu()) dismissMenu();
      else if (renamingId()) setRenamingId(null);
    }
  };
  const onDocClick = (e: MouseEvent) => {
    if (menuRoot && !menuRoot.contains(e.target as Node)) dismissMenu();
  };

  onMount(() => {
    document.addEventListener('keydown', onDocKey);
    document.addEventListener('click', onDocClick, true);
  });
  onCleanup(() => {
    document.removeEventListener('keydown', onDocKey);
    document.removeEventListener('click', onDocClick, true);
    if (blockedTimer != null) clearTimeout(blockedTimer);
  });

  const onTabContextMenu = (id: string, e: MouseEvent) => {
    e.preventDefault();
    openMenu(id, e.currentTarget as HTMLElement);
  };

  const onTabDoubleClick = (id: string, e: MouseEvent) => {
    startRename(id, e.currentTarget as HTMLElement);
  };

  const onDragStart = (index: number, e: DragEvent) => {
    e.dataTransfer?.setData('text/plain', String(index));
    if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
  };

  const onDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
  };

  const onDrop = (toIndex: number, e: DragEvent) => {
    e.preventDefault();
    const from = Number(e.dataTransfer?.getData('text/plain'));
    if (!Number.isNaN(from) && from !== toIndex) {
      props.onReorder(from, toIndex);
    }
  };

  const menuWorkspace = () => {
    const m = menu();
    if (!m) return undefined;
    return props.workspaces.find((w) => w.id === m.id);
  };

  return (
    <div
      class={`workspace-tabbar${props.class ? ` ${props.class}` : ''}`}
      data-workspace-tabbar=""
      data-bar-height={WORKSPACE_BAR_HEIGHT_PX}
    >
      <div class="workspace-tabbar__scroll">
        <For each={props.workspaces}>
          {(ws, index) => {
            const isActive = () => props.activeId === ws.id;
            const isRenaming = () => renamingId() === ws.id;
            return (
              <div
                role="tab"
                class="workspace-tab"
                data-workspace-tab={ws.id}
                data-tab-state={isActive() ? 'active' : 'inactive'}
                data-tab-height={WORKSPACE_TAB_HEIGHT_PX}
                style={{
                  '--workspace-accent': workspaceAccentVar(ws.accentColor),
                }}
                aria-selected={isActive()}
                tabindex={0}
                draggable={!isRenaming()}
                onClick={() => {
                  if (!isRenaming()) props.onActivate(ws.id);
                }}
                onDblClick={(e) => onTabDoubleClick(ws.id, e)}
                onContextMenu={(e) => onTabContextMenu(ws.id, e)}
                onDragStart={(e) => onDragStart(index(), e)}
                onDragOver={onDragOver}
                onDrop={(e) => onDrop(index(), e)}
              >
                <span
                  class="workspace-tab__dot"
                  aria-hidden="true"
                  style={{
                    '--workspace-accent': workspaceAccentVar(ws.accentColor),
                  }}
                />
                <Show
                  when={isRenaming()}
                  fallback={<span class="workspace-tab__name">{ws.name}</span>}
                >
                  <input
                    class="workspace-tab__rename"
                    data-workspace-rename-input=""
                    type="text"
                    value={ws.name}
                    onClick={(e) => e.stopPropagation()}
                    onKeyDown={(e) => {
                      e.stopPropagation();
                      if (e.key === 'Enter') {
                        commitRename(
                          ws.id,
                          (e.currentTarget as HTMLInputElement).value,
                        );
                      }
                      if (e.key === 'Escape') setRenamingId(null);
                    }}
                    onBlur={(e) => commitRename(ws.id, e.currentTarget.value)}
                  />
                </Show>
                <span class="workspace-tab__close-slot">
                  <button
                    type="button"
                    class="workspace-tab__close"
                    data-workspace-tab-close=""
                    aria-label={`Close ${ws.name}`}
                    tabindex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      requestClose(ws.id);
                    }}
                  >
                    ×
                  </button>
                </span>
              </div>
            );
          }}
        </For>
      </div>

      <Show when={blockedCopy()}>
        <span class="workspace-tabbar__blocked" data-workspace-blocked="">
          {blockedCopy()}
        </span>
      </Show>

      <button
        type="button"
        class="workspace-tabbar__add"
        aria-label={COPY_NEW_WORKSPACE}
        onClick={() => props.onNew()}
      >
        +
      </button>

      <Show when={menu()}>
        {(m) => {
          const ws = menuWorkspace();
          return (
            <div
              ref={menuRoot}
              class="workspace-context-menu"
              data-workspace-context-menu=""
              role="menu"
              style={{
                left: `${m().x}px`,
                top: `${m().y}px`,
              }}
            >
              <Show when={m().view === 'main'}>
                <button
                  type="button"
                  role="menuitem"
                  class="workspace-context-menu__row"
                  data-menu-action="rename"
                  onClick={() => {
                    const tabEl = document.querySelector(
                      `[data-workspace-tab="${m().id}"]`,
                    ) as HTMLElement;
                    if (tabEl) startRename(m().id, tabEl);
                  }}
                >
                  {COPY_RENAME_WORKSPACE}
                </button>
                <button
                  type="button"
                  role="menuitem"
                  class="workspace-context-menu__row"
                  data-menu-action="color"
                  onClick={() => setMenu({ ...m(), view: 'color' })}
                >
                  {COPY_COLOR}
                </button>
                <button
                  type="button"
                  role="menuitem"
                  class="workspace-context-menu__row workspace-context-menu__row--destructive"
                  data-menu-action="close"
                  onClick={() => requestClose(m().id)}
                >
                  {COPY_CLOSE_WORKSPACE}
                </button>
                <Show when={blockedCopy()}>
                  <div class="workspace-context-menu__message">{blockedCopy()}</div>
                </Show>
              </Show>

              <Show when={m().view === 'color' && ws}>
                {(active) => (
                  <>
                    <button
                      type="button"
                      class="workspace-context-menu__row"
                      onClick={() => setMenu({ ...m(), view: 'main' })}
                    >
                      ← {COPY_COLOR}
                    </button>
                    <div class="workspace-context-menu__colors">
                      <For each={[...WORKSPACE_ACCENT_COLORS]}>
                        {(color) => (
                          <button
                            type="button"
                            class="workspace-color-dot"
                            data-workspace-color={color}
                            data-selected={
                              active().accentColor === color ? 'true' : 'false'
                            }
                            aria-label={color}
                            style={{
                              '--workspace-dot-color': workspaceAccentVar(color),
                            }}
                            onClick={() => {
                              props.onColor(active().id, color);
                              dismissMenu();
                            }}
                          />
                        )}
                      </For>
                    </div>
                  </>
                )}
              </Show>

              <Show when={m().view === 'confirm-close'}>
                <div class="workspace-close-confirm">
                  <p class="workspace-close-confirm__copy">
                    {COPY_CLOSE_RUNNING_CONFIRM}
                  </p>
                  <div class="workspace-close-confirm__actions">
                    <button
                      type="button"
                      class="workspace-close-confirm__btn"
                      onClick={dismissMenu}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      class="workspace-close-confirm__btn workspace-close-confirm__btn--destructive"
                      data-workspace-close-confirm=""
                      onClick={() => confirmClose(m().id)}
                    >
                      Close
                    </button>
                  </div>
                </div>
              </Show>
            </div>
          );
        }}
      </Show>
    </div>
  );
}
