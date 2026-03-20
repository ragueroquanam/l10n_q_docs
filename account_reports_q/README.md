# Account Reports Q

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.2.0.0  
**Odoo Version:** 18.0

This module provides enhanced accounting reports for the Quanam localization, extending Odoo's standard reporting capabilities with specialized financial reports, statement of changes in equity, and advanced analytics for comprehensive financial reporting.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Statement of Changes in Equity

Comprehensive statement of changes in equity report with detailed tracking of equity movements, capital changes, retained earnings, and other comprehensive income components.

### Advanced Financial Reports

Enhanced financial reporting with customizable report templates, multi-period comparisons, and detailed breakdowns for comprehensive financial analysis.

### Excel Export Capabilities

Native Excel export functionality for all reports, enabling advanced data manipulation, custom formatting, and integration with external analysis tools.

### Configurable Report Parameters

Flexible report configuration system that allows customization of report periods, comparison dates, account groupings, and presentation formats.

### Multi-Period Analysis

Advanced multi-period analysis capabilities with trend analysis, variance reporting, and period-over-period comparisons for better financial insights.

## Configuration

### Report Configuration

1. Go to *Accounting* > *Configuration* > *Statement Change Equity Config*
2. Configure equity account mappings and categories
3. Set up report parameters and presentation options
4. Define calculation rules for equity components

### Account Grouping

1. Configure account groups for report presentation
2. Set up mapping between chart of accounts and report categories
3. Define calculation formulas for derived amounts
4. Configure comparative period parameters

### Report Templates

1. Customize report templates and layouts
2. Configure header information and company details
3. Set up report formatting and presentation options
4. Define export formats and options

## Usage

### Generating Equity Reports

1. Go to *Accounting* > *Reporting* > *Statement Changes Equity*
2. Select reporting period and comparison dates
3. Configure report parameters and options
4. Generate and review the statement of changes in equity

### Excel Export

1. Generate any financial report
2. Use Excel export functionality to download reports
3. Leverage advanced Excel features for further analysis
4. Share reports with stakeholders in Excel format

### Multi-Period Analysis

1. Configure multiple periods for comparison
2. Generate trend reports and variance analysis
3. Analyze period-over-period changes
4. Create dashboard views with key metrics

### Custom Report Configuration

1. Access report configuration wizards
2. Customize report parameters and filters
3. Save custom report configurations for reuse
4. Generate reports with specific requirements

## Technical Details

### Models

* `statement.change.equity.conf`: Equity report configuration
* `statement.changes.equity.wizard`: Report generation wizard

### Reports

* Statement of Changes in Equity (PDF and Excel formats)
* Custom financial reports with enhanced features
* Multi-period comparative reports

### Key Features

* Advanced equity reporting with detailed breakdowns
* Excel export with native formatting
* Configurable report parameters and layouts
* Multi-period analysis and comparison
* Integration with standard Odoo accounting reports

## Dependencies

* `base`: Core Odoo functionality
* `account`: Core accounting functionality
* `report_xlsx`: Excel reporting capabilities

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

