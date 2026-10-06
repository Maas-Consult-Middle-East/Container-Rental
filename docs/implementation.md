# BADR Container implementation

## Inspection and plan
Bench `/Users/macavenue/maas-bench`; site `container.com`; installed apps frappe 15.120.0, erpnext 15.121.0, container 0.0.1. Python 3.14.2, Node 24.20.0. Other discovered sites: helpdesk.com, helpdesk.in, pos, ledes.com, frappe.com; these are outside the migration scope.

Existing untracked schema files belong to the user: Container, Container Type, Container Contract, Contract Type. Controllers and tests were placeholders. No container custom fields, reports, workspace, workflow or fixture logic existed. Database inspection found zero containers/contracts/types and one Unlimited Contract type. Preserve its name and all existing field names. Preserve legacy select options. Fix unused Container.current_contract link from Contract to Container Contract. Keep the existing Container module and expose Container Management through the workspace; avoid a second equivalent module.

Implement operations, accounting adapters, fleet maintenance, permission-aware reporting, workspace and tests in stages. Reuse ERPNext Vehicle as Truck and Driver; do not create another vehicle master. Vehicle already supplies license_plate, last_odometer, insurance dates and Fleet Manager permissions. Reuse Accounts User/Manager for accounting; add only container-specific roles.

## Operational rules
Submit contracts to assign their child containers. Additional deliveries require an active contract. A delivery requires an empty container. Pull/Pickup keeps the assignment until Return. Emptying keeps the rented assignment: it empties contents, not the rental. Replacement records Return and Delivery atomically. Historical contract rows remain unchanged after replacements; the movement ledger and container assignment show the current state.

Draft trips represent planning/in-transit work; submit only Delivered/Returned trips. Both consume one trip. Returned trip status describes the trip; use a Return movement for physical rental termination. Limited contracts use parent trip count or the sum of child counts. Unlimited contracts have no trip cap. Extra trips require a manager-controlled flag and reason. Cancel later dependent movements first; cancellation restores previous state. Scheduled work only marks overdue rentals Late and updates permit expiry status. Contract completion is explicit and requires all containers returned.

Reservations conservatively count currently empty fleet capacity, with inclusive overlap dates and a type-level database lock. Specific reservations require quantity one. Future return forecasts are not treated as guaranteed availability.

## Accounting and business setup
Configure Company, currency, rental Item, tax accounts/templates and standard ERPNext permissions. Contract cost uses ERPNext Sales Invoice tax calculations. Existing Item Tax Template is retained; Sales Taxes and Charges Template supplies invoice tax rows. Explicit exempt contracts clear taxes. Invoice creation makes a draft, never posts accounting automatically. Fixed-trip contracts have one generated invoice; unlimited billing uses an explicit amount and permits repeated invoices. Discounts/charges beyond the agreed contract amount belong on the ERPNext invoice; its ledger is authoritative. Payments and credit notes follow ERPNext. Withdrawal references a submitted customer refund; it does not create a second ledger. Commission is explicitly generated from a selected effective rule and invoice net total, one entry per invoice/salesperson. Paying commissions uses standard accounting.

## Standard report mapping
Do not clone these ERPNext reports. Workspace links preserve ERPNext accounting permissions.

| Requested category | Reused ERPNext source |
| --- | --- |
| Client statement / activity | General Ledger (Party Type Customer, Party filter) |
| Client indebtedness / outstanding payments | Accounts Receivable |
| Receipts / company paid receipts / payment back | Payment Entry list, Payment Type Receive/Pay |
| Cash sales / other income / rent taxes / rent back taxes | Sales Register; Sales Invoice list, Is Return / Is POS filters |
| Payment taxes / payment back taxes | General Ledger and applicable statutory VAT report; cash-basis policy needs confirmation |
| General spending / purchasing | Purchase Register, Accounts Payable |
| Purchase returns | Purchase Invoice list, Is Return filter |
| Stock items | Item list |
| Stock balances | Stock Balance |
| Item transactions / returns | Stock Ledger and Stock Entry list |
| Item purchasing | Item-wise Purchase History |
| Deferred rent | Deferred Revenue report and standard Item deferred revenue settings |
| Salary / employee loans | HRMS/Lending integration required; neither is installed on this site |

Truck oil costs are maintenance records, not posted expenses; Supplier purchasing and GL reports supply accounting expense totals. Expense allocation, salary, loan, cash-basis taxes and automatic recurring unlimited billing need business configuration rather than invented accounting rules.

## Permissions and deployment
Assign Container Operator for daily rentals/movements, Container Manager for cancellation and trip overrides, Container Reports User for operational reading, and standard Fleet Manager / Accounts User / Accounts Manager as appropriate. Users also need standard ERPNext access to the Customer, Item, Company and other linked masters they use. No user is automatically granted a role. General container report readers do not receive commission/refund access. Standard ERPNext financial reports retain their existing permissions.

Open `/app/container-management`. Use the existing Vehicle master through the Trucks link. Set a default Company for the outstanding dashboard card; the card converts contract invoice balances to that company's base currency. Today's Trips excludes cancelled trips. Upcoming fleet maintenance means 30 days or 1,000 KM; these are reporting thresholds, not automatic work orders.

Run `bench --site SITE migrate` and `bench build --app container`. Setup is additive and repeatable; custom fields are created with `update=False`, standard record names are stable, and existing Contract Type records are preserved. No existing user records are deleted or renamed. Legacy status/tax options remain accepted for compatibility. The new canonical defaults are Empty and Exempt.

## Requested report aliases intentionally reused
- Container Search Report → Container Status Report with Report Builder filters.
- Rent Report / Customer Rental Report → Customer Rental Report.
- Pull Report → Pull Containers Report.
- Customer Activity Report → Container Movement Report plus General Ledger customer filter.
- Client Statement Report → General Ledger customer filter.
- Client Indebtedness / Outstanding Payment Report → Accounts Receivable.
- Contracts Payments Report → Contract Payment Report (settled amounts include credits and write-offs; receipt-level detail remains Payment Entry).
- Deferred Rent Report → Deferred Revenue and Expense.
- Receipt / Company Paid Receipt / Payment Back Report → Payment Entry filtered Receive / Pay.
- Cash Sales / Other Income → Sales Register and Sales Invoice filters/accounts.
- Rent Back / Rent Back Taxes → Sales Invoice credit notes and Sales Register.
- Rent Taxes → Sales Register / Item-wise Sales Register.
- General Spending → Purchase Register / General Ledger.
- Truck Expense Report → Truck Spending Report (submitted Purchase Invoices linked to Truck).
- Stock Items → Item list; Stock Balance Report → Stock Balance.
- Item Transaction / Item-wise Transaction / Item Back Transaction → Stock Ledger with item and voucher filters.
- Item Purchasing → Item-wise Purchase History; Purchase / Main Purchasing → Purchase Register.
- Purchasing Return → Purchase Invoice returns.
- Duplicate Emptying Report / Commission Report requests → one report each.

## Verification and limits
Database backup was taken before migration in `sites/container.com/private/backups/20261006_135948-container_com-database.sql.gz`. Migrations were repeated successfully while building the app. Asset build succeeds; the existing Node toolchain emits a `url.parse()` deprecation warning.

Run `bench --site container.com execute container.tests.test_workflows.run` for the integration suite. It uses savepoints and rolls test records back; it requires an existing Company/chart of accounts and standard ERPNext setup. Tests cover rental types, taxes, invoices/payments/outstanding, refunds, commissions, assignment conflicts, reservation overlap/capacity/completion, trip limits/cancellation, pull/return, replacement, emptying, negative values/dates, odometers, late status, contract completion, role permissions, report metadata and workspace/card links.

Production acceptance still needs operator review of forms and print formats, concurrent-user/load testing, real company tax template configuration, and business sign-off on unlimited billing frequency, cash-basis tax reports, reservation completion procedure and commission payout policy. Salary/loan reporting requires HRMS/Lending; these applications were not installed or duplicated. No automated contract closure, commission payment, recurring billing or expense posting was invented. Test-created customers/items/invoices/payments are rolled back; business configuration remains for administrators to populate.

Final verification: **22 integration tests passed**, Ruff passed, Python compilation passed, Git whitespace checks passed, and `bench build --app container` passed. Live metadata contains 16 container-module DocTypes, 22 reports, one Container Management workspace and nine number cards. Post-test verification found zero temporary customers, items, containers, contracts, vehicles, invoices, payments or test users. The original Unlimited Contract record remains; Rubble and Trash were added only if absent.
