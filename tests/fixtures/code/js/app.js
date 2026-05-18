// Minimal JS fixture

function sharedEntry(x) {
  return helperValue(x) + 1;
}

function helperValue(n) {
  return n * 2;
}

class HelperClass {
  method() {
    return "hello";
  }
}

if (require.main === module) {
  console.log(sharedEntry(41));
}
