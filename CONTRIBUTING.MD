# Contributing

Contributions are welcome and greatly appreciated.

## Types of Contributions

### Report Bugs

If you are reporting a bug, please include:

- Your operating system name and version.
- Any details about your local setup that might be helpful in troubleshooting.
- Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug" and "help
wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

Documentation contributions are always welcome, whether to the official docs,
docstrings, blog posts, or articles. The docs are built with
[mkdocs](https://www.mkdocs.org/), and the source files live in the `docs/` directory.

### Submit Feedback

If you are proposing a feature:

- Explain in detail how it would work.
- Keep the scope as narrow as possible, to make it easier to implement.
- This is a public-good project. The tools will always be open source.

## Get Started!

Ready to contribute? Here's how to set up `dcp-tools` for local development.

1. Open an issue in the `dcp-tools` repository to discuss your proposed changes or enhancements.
   This is a good way to get feedback and ensure your work aligns with the project's goals.
2. Fork `dcp-tools` and clone your fork.
1. Dependencies are managed using uv. Install uv in your virtual environment and
   install project dependencies:

```console
uv sync --group dev
```

4. Install the pre-commit hooks so formatting and lint checks run automatically on each commit:

```console
uv run pre-commit install
```

5. Ensure tests are written for any new functionality
   and that existing tests pass. Code coverage is important but not critical. We prioritize
   meaningful tests that cover all major functionality. Code should be formatted
   using `ruff format` and pass `ruff check` and `ty check` to adhere to the project's coding
   standards. CI runs all four (`ruff check`, `ruff format --check`, `ty check`, and `pytest`) on
   every pull request.

1. When you are done developing, open a pull request on the main repository,
   with a clear description of your changes and any relevant issue numbers.
   One of the maintainers will review your changes and provide feedback.

1. If your pull request is accepted, it will be merged into the main branch. Your changes
   will be included in the next release, and your contributions
   will be acknowledged in the project's changelog.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include additional tests if appropriate.
1. If the pull request adds functionality, the docs should be updated.
1. The pull request should work for all currently supported operating systems and versions of Python.
