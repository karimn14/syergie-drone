# Testing in Drone Sawit

## Running Tests

To run the Python tests manually, use:
```sh
pytest
```
Or run specific test files:
```sh
pytest tests/test_sample.py
```

## Continuous Integration (CI)

For robust development, it is recommended to set up Continuous Integration (CI) to run tests automatically on each commit or pull request. Popular options include GitHub Actions, GitLab CI, or Travis CI. See documentation for your chosen platform to get started.

---

This directory contains test scripts for system validation.

- **Unit tests:** Validate individual modules (see `test_sample.py` for examples).
- **Integration tests:** Planned for hardware-in-the-loop and mission simulation.
- **Test coverage:** Expand tests as new modules are added.

> Run tests before deployment to ensure system reliability.
