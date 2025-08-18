# Contributing

When contributing to this repository, please ensure you follow these guidelines:

## Alembic Revisions

If you make any changes to the database models, you must create a new Alembic revision. You can do this by running the following command:

```bash
make add-alembic-revision
```

This will auto-generate a new revision file for your database schema changes.

## Pre-commit Hooks

Before committing your changes, please make sure that all pre-commit hooks are passing. You can run the hooks with the following command:

```bash
make pre-commit
```

This will run a series of checks to ensure code quality and consistency.

## Python Dependencies

If you add or update any Python dependencies, you need to synchronize the `requirements.in` file. You can do this by running:

```bash
make sync-uv-dependencies
```

This will update the `requirements.in` file based on `requirements.txt`. After that, you should run `make install-dependencies` to install the new dependencies.

## Running Tests

To ensure that your changes do not break any existing functionality, please run the test suite before submitting a pull request. You can run the tests with the following command:

```bash
make tests
```

## Sensitive Information

Do not hardcode sensitive information such as API keys, secrets, or passwords in the source code. Use environment variables or a configuration file (e.g., `.env`) to manage these values. Refer to `env_sample` for the required environment variables.
