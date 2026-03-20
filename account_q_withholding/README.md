# Account Q Withholding

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-AGPL--3-blue.png)](http://www.gnu.org/licenses/agpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.1.2.1  
**Odoo Version:** 18.0

This module provides comprehensive tax withholding calculation and management functionality, extending Odoo's standard tax capabilities with advanced withholding tax processing, automatic calculations, and compliance reporting.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Automatic Withholding Calculations

Advanced withholding tax calculation engine that automatically computes withholding amounts based on tax configurations, vendor settings, and regulatory requirements.

### Tax Withholding Management

Comprehensive tax withholding management with support for multiple withholding types, rate configurations, and exemption handling for different vendor categories.

### Compliance and Reporting

Built-in compliance features with automated withholding reports, tax certificates generation, and regulatory reporting to meet local tax authority requirements.

### Account Position Integration

Integration with fiscal positions to automatically apply appropriate withholding tax rules based on vendor location, tax residence, and business relationship type.

### Withholding Certificates

Automated generation of withholding tax certificates and supporting documentation required for vendor payments and tax authority submissions.

## Configuration

### Tax Withholding Setup

1. Go to *Accounting* > *Configuration* > *Taxes*
2. Configure withholding tax types and rates
3. Set up withholding calculation rules and thresholds
4. Configure exemption criteria and special cases

### Account Positions

1. Go to *Accounting* > *Configuration* > *Fiscal Positions*
2. Configure fiscal positions with withholding tax rules
3. Set up automatic tax mapping for withholding scenarios
4. Define position-specific withholding requirements

### Vendor Configuration

1. Go to *Contacts* > *Vendors*
2. Configure vendor-specific withholding settings
3. Set up tax residence and exemption status
4. Configure withholding certificates and documentation

## Usage

### Processing Vendor Bills

1. Create vendor bills as usual
2. System automatically calculates applicable withholding taxes
3. Review withholding amounts and adjustments
4. Post bills with proper withholding tax entries

### Withholding Certificates

1. Go to *Accounting* > *Withholding* > *Certificates*
2. Generate withholding certificates for vendors
3. Print or export certificates for distribution
4. Track certificate status and delivery

### Compliance Reporting

1. Access withholding tax reports from accounting menu
2. Generate periodic withholding summaries
3. Export data for tax authority submissions
4. Monitor compliance status and deadlines

### Payment Processing

1. Process vendor payments with withholding tax deductions
2. Automatic calculation of net payment amounts
3. Generate withholding tax vouchers and documentation
4. Update withholding tax accounts and balances

## Technical Details

### Models

* `account.tax`: Enhanced tax configuration with withholding capabilities
* `account.resguardo`: Withholding tax management and certificates
* `account.fiscal.position`: Enhanced fiscal position with withholding rules
* `account.move`: Extended invoice processing with withholding calculations

### Key Features

* Automatic withholding tax calculations
* Multi-type withholding support (income, VAT, etc.)
* Integration with fiscal positions
* Automated certificate generation
* Compliance reporting and documentation
* Vendor-specific withholding management

## Dependencies

* `account`: Core accounting functionality
* `account_q`: Enhanced accounting features

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

This module is licensed under AGPL-3.

