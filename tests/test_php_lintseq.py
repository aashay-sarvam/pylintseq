import unittest
import tempfile
import os
import subprocess
import json
from src.pylintseq.utils import file_linter, lintseq_backward_sampling, inflate_edit_path

# Helper function to check if phpcs is available
def is_phpcs_available():
    """Checks if phpcs is installed and available in the PATH."""
    try:
        # Using a command that gives a quick success/fail and version info
        # phpcs --version exits with 0 on success.
        subprocess.run(["phpcs", "--version"], capture_output=True, check=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

@unittest.skipUnless(is_phpcs_available(), "PHP_CodeSniffer (phpcs) not found. Skipping PHP linting tests.")
class TestPHPLinting(unittest.TestCase):

    def test_basic_php_linting_error(self):
        """Test file_linter with a PHP snippet having a common error."""
        # PHPCS error: Using undefined variable $undefined_variable.
        php_code_with_error = "<?php echo $undefined_variable; ?>"

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".php", delete=False) as tmp_file:
            tmp_file.write(php_code_with_error)
            tmp_file_path = tmp_file.name
        
        try:
            errors = file_linter(tmp_file_path, language="php")
            self.assertTrue(len(errors) > 0, f"Should find at least one linting error. Errors: {errors}")
            # Example check for undefined variable error from PHPCS
            # The 'source' can be something like 'PHPCompatibility.PHP.NewIniDirectives.error_reportingDeprecated'
            # or specific to the coding standard used (e.g., PSR12).
            # For an undefined variable, it's often a generic PHP parse/runtime-level notice reported by phpcs.
            # A common 'source' for undefined variables might be related to 'Squiz.Scope.StaticThisUsageNotAllowed'
            # or more generically a notice that phpcs picks up if error reporting is high enough.
            # Let's check for a message containing "Undefined variable".
            found_expected_error = False
            for error in errors:
                # error format is (msg_id, line_id, column_id, msg)
                if "Undefined variable".lower() in error[3].lower() and "$undefined_variable" in error[3]:
                    found_expected_error = True
                    break
            self.assertTrue(found_expected_error, f"Did not find expected 'Undefined variable' error. Errors: {errors}")
        finally:
            os.remove(tmp_file_path)

    def test_php_missing_semicolon(self):
        """Test file_linter with a PHP snippet having a syntax error (missing semicolon)."""
        php_code_syntax_error = "<?php echo 'Hello'\n echo 'World'; ?>" # Missing semicolon after 'Hello'

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".php", delete=False) as tmp_file:
            tmp_file.write(php_code_syntax_error)
            tmp_file_path = tmp_file.name
        
        try:
            errors = file_linter(tmp_file_path, language="php")
            self.assertTrue(len(errors) > 0, f"Should find at least one syntax error. Errors: {errors}")
            # PHPCS often reports syntax errors with a source like 'PHP.Parser.Syntax' or similar
            found_syntax_error = False
            for error in errors:
                if "syntax error".lower() in error[3].lower() or "parse error".lower() in error[3].lower():
                    found_syntax_error = True
                    break
            self.assertTrue(found_syntax_error, f"Did not find expected syntax error. Errors: {errors}")
        finally:
            os.remove(tmp_file_path)

    def test_php_no_linting_errors(self):
        """Test file_linter with a correct PHP snippet."""
        php_code_correct = "<?php\n$a = 1;\necho \"Hello, world! \" . $a;\n?>"
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".php", delete=False) as tmp_file:
            tmp_file.write(php_code_correct)
            tmp_file_path = tmp_file.name
        
        try:
            errors = file_linter(tmp_file_path, language="php")
            self.assertEqual(len(errors), 0, f"Should find no linting errors. Errors: {errors}")
        finally:
            os.remove(tmp_file_path)

    def test_lintseq_backward_sampling_php(self):
        """Test lintseq_backward_sampling with a simple PHP snippet."""
        php_snippet = "<?php\nfunction greet($name) {\n  return \"Hello, \" . $name;\n}\necho greet(\"PHP\");\n?>"
        
        edit_path_info = lintseq_backward_sampling(
            php_snippet, 
            language="php",
            children_per_round=1,
            top_k=1,
            max_population_size=1
        )
        
        self.assertIsNotNone(edit_path_info, "lintseq_backward_sampling should return a result for PHP.")
        self.assertTrue(isinstance(edit_path_info, list) and len(edit_path_info) > 0, "Result should be a non-empty list (population).")

        edit_sequence, _, _ = edit_path_info[0]
        self.assertTrue(isinstance(edit_sequence, list), "Edit sequence should be a list.")
        
        # Test inflation (optional but good check)
        raw_text_seq, _ = inflate_edit_path(php_snippet, edit_sequence)
        self.assertTrue(len(raw_text_seq) > 0)
        self.assertEqual(raw_text_seq[0].strip(), "", "Applying all backward edits should result in an empty string (or whitespace).")
        # For PHP, the final state might be "<?php\n?>" or just whitespace if the snippet is wrapped in tags.
        # If the original snippet includes <?php ?>, the backward sampling might result in just those tags or empty.
        # For this test, let's assume it should reduce to minimal valid PHP (empty script) or nothing.
        self.assertEqual(raw_text_seq[-1], php_snippet, "Last element of raw sequence should be original snippet.")


    def test_lintseq_empty_php_code(self):
        """Test lintseq_backward_sampling with empty PHP code."""
        php_snippet = "" # Truly empty
        edit_path_info = lintseq_backward_sampling(php_snippet, language="php")
        self.assertEqual(edit_path_info, [([], [], [])], "Should return the specific structure for empty input.")

        php_snippet_whitespace = "   " # Whitespace only
        edit_path_info_ws = lintseq_backward_sampling(php_snippet_whitespace, language="php")
        self.assertEqual(edit_path_info_ws, [([], [], [])], "Should return the specific structure for whitespace-only input.")

        php_snippet_empty_tags = "<?php\n?>" # Empty PHP tags
        edit_path_info_tags = lintseq_backward_sampling(php_snippet_empty_tags, language="php")
        self.assertIsNotNone(edit_path_info_tags)
        self.assertTrue(len(edit_path_info_tags) > 0)
        # For "<?php\n?>", the edit sequence might not be empty if it considers the tags as lines.
        # The core logic `if not code_as_text.strip(): return [([], [], [])]` handles fully empty/whitespace.
        # If it's just tags, it proceeds. For this test, let's ensure it doesn't fail.
        self.assertTrue(isinstance(edit_path_info_tags[0][0], list))


if __name__ == '__main__':
    unittest.main()
