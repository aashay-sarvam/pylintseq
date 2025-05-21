import unittest
import tempfile
import os
import subprocess
import json
from src.pylintseq.utils import file_linter, lintseq_backward_sampling, inflate_edit_path

# Helper function to check if ESLint is available
def is_eslint_available():
    """Checks if eslint is installed and available in the PATH."""
    try:
        subprocess.run(["eslint", "--version"], capture_output=True, check=True, text=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

class TestJavaScriptLinting(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Skip all tests in this class if ESLint is not available."""
        if not is_eslint_available():
            raise unittest.SkipTest("ESLint not found. Skipping JavaScript linting tests.")

    def test_basic_javascript_linting_error(self):
        """Test file_linter with a JS snippet having a common error."""
        # ESLint error: 'b' is not defined. (no-undef)
        # For ESLint v6.4.0, a syntax error is more reliable to detect without specific config.
        js_code_with_error = "const a = {;" 

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".js", delete=False) as tmp_file:
            tmp_file.write(js_code_with_error)
            tmp_file_path = tmp_file.name
        
        try:
            errors = file_linter(tmp_file_path, language="javascript")
            self.assertTrue(len(errors) > 0, "Should find at least one linting error.")
            # Example check, this might need adjustment based on actual ESLint output
            # For ESLint 6.4.0, a syntax error often results in a message starting with "Parsing error:"
            # The error format is (msg_id, line_id, column_id, msg)
            # msg_id for parsing error is often None or not standardized, so checking the message text.
            found_expected_error = False
            for error in errors:
                if "parsing error" in error[3].lower(): # Check the message field
                    found_expected_error = True
                    break
            self.assertTrue(found_expected_error, f"Did not find expected 'Parsing error'. Errors: {errors}")
        finally:
            os.remove(tmp_file_path)

    def test_javascript_no_linting_errors(self):
        """Test file_linter with a correct JS snippet."""
        js_code_correct = "'use strict';\nconst a = 1;\nlet b = a + 2;\nfunction greet(c) { return c; }\ngreet(b);"
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".js", delete=False) as tmp_file:
            tmp_file.write(js_code_correct)
            tmp_file_path = tmp_file.name
        
        try:
            errors = file_linter(tmp_file_path, language="javascript")
            self.assertEqual(len(errors), 0, f"Should find no linting errors. Errors: {errors}")
        finally:
            os.remove(tmp_file_path)

    def test_lintseq_backward_sampling_javascript(self):
        """Test lintseq_backward_sampling with a simple JavaScript snippet."""
        js_snippet = "function multiply(a, b) {\n  return a * b;\n}\nmultiply(2, 3);"
        
        # lintseq_backward_sampling expects code_as_text, not a file path
        edit_path_info = lintseq_backward_sampling(
            js_snippet, 
            language="javascript",
            children_per_round=1, # Keep params simple for testing
            top_k=1,
            max_population_size=1
        )
        
        self.assertIsNotNone(edit_path_info, "lintseq_backward_sampling should return a result.")
        self.assertTrue(isinstance(edit_path_info, list), "Result should be a list (population).")
        # If population is empty, it means no valid path was found, which could be an issue.
        # For this simple snippet, we expect it to find a path.
        self.assertTrue(len(edit_path_info) > 0, "Population should not be empty for a valid snippet.")

        # Check structure of the first (and likely only) path in the population
        edit_sequence, remaining_lines, integrated_edit = edit_path_info[0]
        self.assertTrue(isinstance(edit_sequence, list), "Edit sequence should be a list.")
        
        # Test inflation (optional but good check)
        raw_text_seq, diff_seq = inflate_edit_path(js_snippet, edit_sequence)
        self.assertTrue(len(raw_text_seq) > 0)
        self.assertEqual(raw_text_seq[0], "", "Applying all backward edits should result in an empty string.")
        self.assertEqual(raw_text_seq[-1], js_snippet, "Last element of raw sequence should be original snippet.")


    def test_lintseq_empty_javascript_code(self):
        """Test lintseq_backward_sampling with empty JavaScript code."""
        js_snippet = ""
        edit_path_info = lintseq_backward_sampling(js_snippet, language="javascript")
        
        self.assertIsNotNone(edit_path_info, "Should return a result for empty string.")
        # For an empty string, it might return an empty population or a population with an empty edit sequence
        if edit_path_info: # If population is not empty
            self.assertTrue(isinstance(edit_path_info, list))
            if edit_path_info[0][0]: # If edit_sequence is not empty
                 self.assertEqual(len(edit_path_info[0][0]), 0, "Edit sequence for empty code should be empty.")
        # Or, it could be that an empty population is the valid result for an empty input.
        # Based on current understanding, an empty population means failure to find a path.
        # For an empty input, an empty edit sequence IS the path.
        self.assertTrue(len(edit_path_info) > 0, "Population should not be empty for empty input.")
        self.assertEqual(len(edit_path_info[0][0]), 0, "Edit sequence for empty input should be empty.")


if __name__ == '__main__':
    unittest.main()
