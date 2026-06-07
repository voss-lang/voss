module.exports = {
  forbidden: [
    {
      name: "core-no-node-builtins",
      severity: "error",
      comment: "Core entrypoint must stay browser-safe.",
      from: { path: "^dist/index\\.js$" },
      to: {
        dependencyTypes: ["core"],
      },
    },
  ],
  options: {
    moduleSystems: ["es6"],
  },
};
