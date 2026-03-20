# POS Q

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.1.1.0  
**Odoo Version:** 18.0

This module provides enhanced POS (Point of Sale) configurations for the Quanam localization, extending Odoo's standard POS functionality with advanced payment processing, transaction logging, and multi-currency support.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Enhanced Payment Processing

Configure advanced payment methods and terminals with support for multiple payment providers. The system provides seamless integration with various payment terminals and processors.

### Transaction Logging

Comprehensive transaction logging system that tracks all POS operations, providing detailed audit trails and transaction history for compliance and analysis purposes.

### Multi-Currency Support

Full support for multi-currency transactions with real-time currency conversion rates and automatic account selection based on the transaction currency.

### Payment Provider Integration

Advanced integration with multiple payment providers, enabling flexible payment processing options including credit cards, digital wallets, and other electronic payment methods.

### Payment Terminal Management

Centralized management of payment terminals with configuration options for different terminal types, connection settings, and operational parameters.

## Configuration

### Payment Providers

1. Go to *Point of Sale* > *Configuration* > *Payment Providers*
2. Configure your payment provider settings
3. Set up provider-specific parameters and credentials
4. Test the connection to ensure proper integration

### Payment Terminals

1. Go to *Point of Sale* > *Configuration* > *Payment Terminals*
2. Create new payment terminal configurations
3. Configure terminal-specific settings and connection parameters
4. Associate terminals with appropriate payment providers

### Currency Configuration

1. Go to *Point of Sale* > *Configuration* > *Currencies*
2. Enable multi-currency support in POS settings
3. Configure exchange rate sources and update frequencies
4. Set default currencies for different store locations

## Usage

### Processing Payments

1. In the POS interface, select products and finalize the order
2. Choose payment method from configured providers
3. The system automatically handles currency conversion if needed
4. Complete the transaction and generate receipt

### Transaction Monitoring

1. Access *Point of Sale* > *Reporting* > *Transaction Logs*
2. Review detailed transaction history and audit trails
3. Filter transactions by date, terminal, or payment method
4. Export transaction data for external analysis

### Terminal Management

1. Monitor terminal status from the POS dashboard
2. Configure terminal-specific settings as needed
3. Troubleshoot connection issues using diagnostic tools
4. Update terminal firmware and configurations remotely

## Technical Details

### Models

* `pos.transaction.log`: Comprehensive transaction logging
* `pos.transaction`: Enhanced transaction processing
* `pos.payment.provider`: Payment provider configuration
* `pos.payment.terminal`: Payment terminal management
* `res.currency`: Enhanced currency handling for POS

### Key Features

* Advanced payment processing with multiple providers
* Comprehensive transaction logging and audit trails
* Multi-currency support with automatic conversion
* Payment terminal management and monitoring
* Enhanced security and compliance features

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

