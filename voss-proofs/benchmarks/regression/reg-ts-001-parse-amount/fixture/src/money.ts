export function parseAmount(input: string): number {
  return Number(input.replace("$", ""));
}
