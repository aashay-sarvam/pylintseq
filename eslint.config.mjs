// eslint.config.mjs
export default [
  {
    // This configuration block applies to all files ESLint processes.
    // By not specifying a "files" glob pattern, it defaults to matching all files
    // passed to ESLint, which is what we need for temporary files.
    rules: {
      "no-undef": "error", // Example: catch undefined variables
      // Add a rule that would be triggered by "const a = {;"
      // ESLint's parser itself should catch syntax errors without a specific rule.
    },
    languageOptions: {
        ecmaVersion: "latest",
        sourceType: "script" // Treat files as standalone scripts
    }
  }
];
