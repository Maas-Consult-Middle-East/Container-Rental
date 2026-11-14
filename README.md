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

### Tax and price list fixtures

The app includes the `VAT-15%` Tax Category, `VAT-15% - BC` Sales Taxes and
Charges Template, `Vat - BC` Item Tax Template, and the Standard Buying and
Standard Selling price lists in SAR. Frappe imports these fixtures on installation
and migration; matching records are managed by the app and may be overwritten.

These tax templates preserve the source site's configuration: 15% against
`Freight and Forwarding Charges - BC` for `BADR CONTAINER`, with `Main - BC` as
the sales tax cost center. The destination site must have that company, account,
and cost center before using the templates. Review the tax account mapping before
posting invoices. Company and chart-of-accounts records are not exported.

To refresh the selected fixtures after changing them on the source site:

```sh
bench --site container.com export-fixtures --app container
```

Price lists contain currency and selling/buying settings, not individual Item
Prices. New Containers create their own Item and selling Item Price of 500.
