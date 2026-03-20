# Account Check Q

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.1.0.0  
**Odoo Version:** 18.0

This module provides enhanced check management functionality for the Quanam localization, extending Odoo's standard payment capabilities with advanced check processing, tracking, and management features.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Advanced Check Processing

Comprehensive check management system with support for both issued and received checks, check printing, and automated check number sequencing.

### Check Status Tracking

Complete check lifecycle tracking from issuance to clearing, with status updates, hold management, and reconciliation capabilities.

### Check Register Management

Enhanced check register functionality with detailed check logs, batch processing capabilities, and comprehensive reporting for audit and compliance purposes.

### Payment Integration

Seamless integration with Odoo's payment processing system, enabling checks as a standard payment method with full accounting integration.

### Check Printing

Built-in check printing functionality with customizable check formats, alignment options, and support for various check paper types.

## Configuration

### Journal Configuration

1. Go to *Accounting* > *Configuration* > *Journals*
2. Configure check-specific journal settings
3. Set up check number sequences and formatting
4. Enable check printing and processing features

### Check Format Setup

1. Configure check printing formats and layouts
2. Set up check paper dimensions and alignment
3. Customize check content and positioning
4. Test check printing with sample checks

### Payment Method Configuration

1. Configure check payment methods
2. Set up check-specific validation rules
3. Enable check processing workflows
4. Configure check status tracking

## Usage

### Issuing Checks

1. Create vendor payments using check payment method
2. System automatically assigns check numbers
3. Print checks using configured formats
4. Track check status and delivery

### Check Registration

1. Register checks in the check register
2. Update check status as they progress through banking
3. Handle check returns and stop payments
4. Reconcile cleared checks with bank statements

### Check Reconciliation

1. Import bank statements with check clearing information
2. Match cleared checks to outstanding check records
3. Update check status automatically
4. Handle exceptions and discrepancies

### Reporting

1. Generate check registers and reports
2. Monitor outstanding checks and aging
3. Track check processing performance
4. Analyze check usage patterns

## Technical Details

### Models

* Enhanced `account.journal`: Extended with check-specific functionality
* Enhanced `account.payment`: Added check processing capabilities
* Enhanced `account.payment.register`: Improved payment registration with check support

### Key Features

* Complete check lifecycle management
* Automated check numbering and sequencing
* Check printing with customizable formats
* Integration with banking and reconciliation
* Comprehensive check reporting and analytics

## Dependencies

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

