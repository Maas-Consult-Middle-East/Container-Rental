### Container

Frappe app for container rental management

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app container
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/container
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### CI

This app can use GitHub Actions for CI. The following workflows are configured:

- CI: Installs this app and runs unit tests on every push to `develop` branch.
- Linters: Runs [Frappe Semgrep Rules](https://github.com/frappe/semgrep-rules) and [pip-audit](https://pypi.org/project/pip-audit/) on every pull request.


### License

mit

### BADR Container Management

Open **Container Management** in Desk. Reuses ERPNext Vehicle for trucks and Sales Invoice / Payment Entry for accounting.

- [Simple user guide and daily workflow](docs/user_guide.md)
- [Technical implementation and operating notes](docs/implementation.md)

```sh
bench --site container.com migrate
bench build --app container
bench --site container.com execute container.tests.test_workflows.run
```
# Container-Rental
