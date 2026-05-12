```markdown
# THE-JUDGE Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the THE-JUDGE Python codebase. It covers file organization, code style, commit practices, and testing approaches, enabling contributors to write consistent, maintainable code and collaborate effectively.

## Coding Conventions

### File Naming
- Use **snake_case** for all file names.
  - Example: `judge_core.py`, `case_handler.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .utils import parse_case
    from .models import JudgeResult
    ```

### Export Style
- Use **named exports** by explicitly listing public objects in `__all__`.
  - Example:
    ```python
    __all__ = ["Judge", "Case", "evaluate_case"]
    ```

### Commit Messages
- Follow **conventional commit** style.
- Use the `fix` prefix for bug fixes.
  - Example:
    ```
    fix: handle edge case when input is empty
    ```

## Workflows

### Code Contribution
**Trigger:** When adding or updating code
**Command:** `/contribute`

1. Create a new branch for your feature or fix.
2. Follow coding conventions for file naming, imports, and exports.
3. Write or update tests as needed (see Testing Patterns).
4. Commit changes using the conventional commit style.
5. Open a pull request for review.

### Bug Fixing
**Trigger:** When fixing a bug
**Command:** `/fix-bug`

1. Identify the bug and create a branch named `fix/<short-description>`.
2. Make the necessary code changes.
3. Write or update tests to cover the fix.
4. Commit with a message like:
    ```
    fix: resolve issue with judge scoring logic
    ```
5. Open a pull request.

## Testing Patterns

- Test files use the pattern `*.test.*` (e.g., `judge_core.test.py`).
- The testing framework is not explicitly specified; use standard Python testing practices.
- Place tests alongside the code or in a dedicated test directory.
- Example test file:
    ```python
    # judge_core.test.py

    from .judge_core import Judge

    def test_judge_evaluation():
        judge = Judge()
        assert judge.evaluate("case1") == "PASS"
    ```

## Commands
| Command      | Purpose                                 |
|--------------|-----------------------------------------|
| /contribute  | Start a new code contribution workflow  |
| /fix-bug     | Initiate a bug fixing workflow          |
```
