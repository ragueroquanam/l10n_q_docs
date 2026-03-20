# Account Batch Payment Q - Itaú

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.1.0.0  
**Odoo Version:** 18.0

This module provides Itaú Bank specific batch payment file generation, extending the base batch payment functionality with Itaú-compliant file formats and integration protocols.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Itaú File Format Compliance

Generates batch payment files in Itaú's specific format requirements, ensuring compliance with bank specifications and successful file processing.

### Automated File Generation

Automated generation of Itaú-compliant payment files with proper field mapping, validation, and formatting according to bank requirements.

### Pre-configured Settings

Pre-configured Itaú-specific settings including file structure, field positions, data formats, and validation rules to minimize setup time.

### Validation and Error Checking

Comprehensive validation system that checks file content, format compliance, and data integrity before file generation to prevent processing errors.

## Configuration

### Itaú Configuration

The module comes pre-configured with Itaú-specific settings:
- File format specifications
- Field mapping and positioning
- Data validation rules
- Bank-specific requirements

### Bank Account Setup

1. Ensure your bank accounts are configured for Itaú
2. Verify account numbers and routing information
3. Set up Itaú-specific account parameters
4. Test connectivity and file format compliance

## Usage

### Generating Itaú Payment Files

1. Create batch payments as usual
2. Select Itaú as the target bank
3. Generate payment files using Itaú format
4. Submit files to Itaú systems for processing

### File Validation

1. System automatically validates Itaú format compliance
2. Review validation results and error messages
3. Correct any issues before file submission
4. Confirm file integrity and format accuracy

## Technical Details

### File Format Specifications

* Itaú-specific file structure and layout
* Field positioning and data formatting
* Header and trailer record requirements
* Validation checksums and control fields

### Key Features

* Pre-configured Itaú file format
* Automated field mapping and validation
* Bank-specific data formatting
* Compliance with Itaú technical specifications

## Dependencies

* `account_batch_payment_q`: Base batch payment functionality

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

