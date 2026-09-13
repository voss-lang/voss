import type { CommandCategory, CommandRegistry } from './registry';

// Menu model (pure, testable)

export interface NativeMenuItem {
  id: string;
  label: string;
  accelerator?: string;
}

export interface NativeMenuGroup {
  label: string;
  items: NativeMenuItem[];
}

/** Fixed category order matching */
const CATEGORY_ORDER: CommandCategory[] = [
  'Window',
  'Workspace',
  'Pane',
  'Layout',
  'Project',
  'Settings',
  'Help',
];

export function chordToAccelerator(chord: string): string {
  return chord
    .replace('Cmd', 'CmdOrCtrl')
    .replace('Arrow', '');
}

/**
 * Build a pure menu model from registry metadata. No Tauri dependency
 * Each command becomes a menu item; groups follow CATEGORY_ORDER
 */
export function buildNativeMenuModel(
  registry: CommandRegistry,
): NativeMenuGroup[] {
  return CATEGORY_ORDER.map((cat) => ({
    label: cat,
    items: registry.byCategory(cat).map((cmd) => ({
      id: cmd.id,
      label: cmd.label,
      accelerator: cmd.keybinding
        ? chordToAccelerator(cmd.keybinding)
        : undefined,
    })),
  })).filter((g) => g.items.length > 0);
}

// Tauri installation (side-effect, not unit-testable)

/**
 * Install the native OS menu from registry metadata
 * Requires live Tauri runtime no-ops silently in non-Tauri environments
 */
export async function setAsAppMenu(
  registry: CommandRegistry,
  onMenuAction: (commandId: string) => void,
): Promise<void> {
  try {
    const { Menu, Submenu, MenuItem } = await import('@tauri-apps/api/menu');
    const model = buildNativeMenuModel(registry);

    const submenus = await Promise.all(
      model.map(async (group) => {
        const items = await Promise.all(
          group.items.map((item) =>
            MenuItem.new({
              id: item.id,
              text: item.label,
              accelerator: item.accelerator,
              action: () => onMenuAction(item.id),
            }),
          ),
        );
        return Submenu.new({ text: group.label, items });
      }),
    );

    const menu = await Menu.new({ items: submenus });
    await menu.setAsAppMenu();
  } catch (e) {
    // Non-Tauri environment (dev server, test) silently skip
    console.warn('[voss-app] native menu setup skipped:', e);
  }
}
