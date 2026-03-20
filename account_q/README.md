# Account Q

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-AGPL--3-blue.png)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/account_q)

**Version:** 18.0.1.2.6  
**Odoo Version:** 18.0

This module extends Odoo's accounting functionality to provide enhanced
multi-currency support for customer and supplier accounts, automatic tax
refund processing, and advanced payment management features.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Multi-Currency Account Management

Configure multiple receivable and payable accounts per partner and currency.
The system automatically selects the appropriate account based on the currency
and partner type, with support for credit card accounts in addition to
standard receivable/payable accounts.

### Tax Refund Management

Configure tax refund legislation with specific document types and tax
combinations. The system automatically detects applicable tax refunds during
payment processing and provides warnings for mixed tax refund scenarios.

### Advanced Payment Processing

Process multiple invoices simultaneously with the multi-invoice payment wizard,
generate automatic debit payments for recurring transactions, and implement
payment blocking functionality to prevent unauthorized payments.

### Document Processing

Automatically extract document numbers from references, process intercompany
invoices with proper document types, and post draft entries via cron jobs.

## Configuration

### Multi-Currency Accounts

1. Go to *Contacts* > *Contacts*
2. Open a partner form
3. In the *Accounting* tab, configure accounts for each currency
4. Set up both receivable and payable accounts for each currency

### Tax Refund Configuration

1. Go to *Accounting* > *Configuration* > *Devolución de impuesto*
2. Create tax refund legislation configurations
3. Specify document types, applicable taxes, and maximum amounts
4. Configure payment methods to apply tax refunds

### Taxable Amount Configuration

1. Go to *Accounting* > *Configuration* > *Settings*
2. In the *Taxes* section, configure *Impuestos Gravables*
3. Select taxes that should be considered for taxable amount calculation

## Usage

### Multi-Currency Payments

When creating payments, the system automatically selects the appropriate
account based on the partner, currency, and payment type. The system
looks for partner-specific accounts first, then falls back to default
accounts.

### Tax Refund Processing

1. Configure tax refund legislation in the system
2. Set up payment methods with tax refund capabilities
3. When processing payments, the system automatically detects applicable refunds
4. For mixed scenarios, the system provides warnings and confirmation dialogs

### Multi-Invoice Payments

1. Select multiple invoices from the invoice list view
2. Click *Pagar en múltiples formas* button
3. Configure payment lines with different journals and methods
4. The system automatically distributes payments across invoices

### Payment Blocking

1. Select invoices that should be blocked for payment
2. Use the *Des(Bloquear Pago)* button to toggle payment blocking
3. Blocked invoices cannot be paid until unblocked
4. The system prevents payment registration for blocked invoices

### Automatic Debit Payments

1. Go to *Accounting* > *Customers* > *Pagos por Débito Automático*
2. Configure journal and payment method
3. Set payment date
4. The system generates payments for all eligible invoices

### Document Processing

The system automatically:
* Extracts document numbers from invoice references
* Processes intercompany invoices with proper document types
* Posts draft entries based on configured rules
* Computes appropriate accounts for payment terms

## Technical Details

### Models

* `res.partner.account`: Multi-currency account configuration for partners
* `tax.refund.legislation.config`: Tax refund legislation configuration
* `multi.invoice.payment.wizard`: Wizard for multi-invoice payments
* `automatic.debit.payment.wizard`: Wizard for automatic debit payments
* `vat.refund.confirmation.wizard`: Confirmation dialog for tax refund scenarios

### Key Features

* Automatic account computation with fallback logic
* Multi-currency support with partner-specific accounts
* Tax refund detection and processing
* Payment blocking and validation
* Enhanced document processing
* Automatic posting via cron jobs

## Dependencies

* `account`: Core accounting functionality
* `l10n_latam_invoice_document`: Latin American document support

## Credits

**Authors:**
* Quanam

**Contributors:**
* Quanam Development Team

**Maintainers:**
This module is maintained by Quanam.

Quanam is a company specialized in Odoo development and implementation.

## Credits

**Authors:**
* Quanam

**Contributors:**
* Quanam Development Team

**Maintainers:**
This module is maintained by Quanam.

Quanam is a company specialized in Odoo development and implementation.

This module is part of the [Quanam/account_q](https://github.com/Quanam/account_q) project on GitHub.

You are welcome to contribute. To learn how please visit [Quanam](https://quanam.com).

## License

This module is licensed under AGPL-3.
