# Cash Management Q

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.2.6.0  
**Odoo Version:** 18.0

This module provides comprehensive cash management functionality for small cash (petty cash) and central cash operations, extending Odoo's accounting capabilities with advanced cash flow control, session management, and multi-location cash handling.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Petty Cash Management

Complete petty cash management system with session-based controls, opening and closing procedures, and detailed cash movement tracking for small daily operations.

### Central Cash Operations

Advanced central cash management with multi-location support, fund transfers between cash points, and centralized cash flow oversight.

### Session Management

Comprehensive cash session management with opening control wizards, session validation, and automatic reconciliation procedures to ensure cash accuracy.

### Cash Fund Transfers

Seamless cash transfers between different cash funds and locations with proper accounting entries, approval workflows, and transfer documentation.

### Dashboard and Reporting

Real-time cash management dashboard with visual indicators, cash position summaries, and comprehensive reporting tools for cash flow analysis.

### Bill and Payment Integration

Integration with bill management and payment processing, enabling direct cash payments from the cash management interface with automatic accounting entries.

## Configuration

### Cash Management Setup

1. Go to *Accounting* > *Configuration* > *Settings*
2. Enable Cash Management features in the accounting settings
3. Configure cash management parameters and default accounts
4. Set up user permissions for cash operations

### Cash Fund Configuration

1. Go to *Cash Management* > *Configuration* > *Cash Funds*
2. Create cash fund configurations for each location
3. Set up opening balances and maximum cash limits
4. Configure approval levels for cash operations

### Payment Methods

1. Go to *Cash Management* > *Configuration* > *Payment Methods*
2. Configure cash-specific payment methods
3. Set up integration with accounting journals
4. Define validation rules for cash payments

## Usage

### Opening Cash Session

1. Go to *Cash Management* > *Sessions*
2. Click *New Session* to start a cash session
3. Use the opening control wizard to set initial cash amounts
4. Validate the opening balance and start operations

### Processing Cash Payments

1. Access the cash management interface
2. Select bills or create new payment entries
3. Process cash payments with automatic accounting integration
4. Track all cash movements in real-time

### Cash Fund Transfers

1. Go to *Cash Management* > *Fund Transfers*
2. Create new transfer between cash funds
3. Specify transfer amounts and purpose
4. Complete transfer with proper documentation

### Session Closing

1. Count physical cash at end of session
2. Use closing wizard to validate cash amounts
3. Reconcile any differences with proper justification
4. Close session and generate closing reports

## Technical Details

### Models

* `cash.management.session`: Cash session management
* `cash.management.config`: Cash fund configuration
* `cash.management.bill`: Bill processing integration
* `cash.fund.transfer`: Inter-fund transfer management
* `payment.method`: Enhanced payment method configuration

### Key Features

* Session-based cash control with opening/closing procedures
* Multi-location cash fund management
* Integrated bill processing and payment handling
* Real-time cash position monitoring
* Automated accounting entry generation
* Comprehensive audit trails and reporting

## Dependencies

* `base`: Core Odoo functionality
* `account`: Core accounting functionality

## Credits

**Authors:**
* Quanam

**Contributors:**
* Quanam Development Team

**Maintainers:**
This module is maintained by Quanam.

Quanam is a company specialized in Odoo development and implementation.

This module is part of the [Quanam/l10n_q](https://github.com/Quanam/l10n_q) project on GitHub.

You are welcome to contribute. To learn how please visit [Quanam](https://quanam.com).

## License

This module is licensed under LGPL-3.

