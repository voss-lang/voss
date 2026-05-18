// Minimal TS fixture

export function sharedEntry(x: number): number {
  return helperValue(x) + 1;
}

function helperValue(n: number): number {
  return n * 2;
}

export class HelperClass {
  method(): string {
    return "hello";
  }
}

if (require.main === module) {
  console.log(sharedEntry(41));
}
