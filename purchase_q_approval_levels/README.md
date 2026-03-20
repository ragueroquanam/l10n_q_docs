# Purchase Q Approval Levels

[![Maturity](https://img.shields.io/badge/maturity-Production%2FStable-green.png)](https://odoo-community.org/page/development-status)
[![License](https://img.shields.io/badge/licence-LGPL--3-blue.png)](http://www.gnu.org/licenses/lgpl-3.0-standalone.html)
[![GitHub](https://img.shields.io/badge/github-Quanam-lightgray.png?logo=github)](https://github.com/Quanam/l10n_q)

**Version:** 18.0.1.0.0  
**Odoo Version:** 18.0

This module extends the Purchase Q functionality by adding sophisticated approval level management for purchase orders, providing multi-level approval workflows, amount-based approval rules, and automated notification systems.

## Table of contents

- [Features](#features)
- [Configuration](#configuration)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Dependencies](#dependencies)
- [Credits](#credits)
- [License](#license)

## Features

### Multi-Level Approval Workflow

Sophisticated approval workflow system with configurable approval levels based on purchase order amounts, vendor categories, and organizational hierarchy.

### Amount-Based Approval Rules

Flexible approval rules that automatically route purchase orders to appropriate approvers based on order values, with configurable thresholds and escalation procedures.

### Automated Notifications

Comprehensive notification system that automatically alerts approvers via email when purchase orders require their attention, with customizable email templates and escalation timers.

### Approval Tracking

Complete approval tracking with audit trails, approval history, and status monitoring to ensure transparency and accountability in the approval process.

### Delegation Management

Advanced delegation capabilities that allow approvers to delegate approval authority temporarily or permanently, ensuring continuous workflow operation.

## Configuration

### Approval Level Setup

1. Go to *Purchase* > *Configuration* > *Approval Levels*
2. Create approval level configurations
3. Define approval thresholds and rules
4. Set up approver assignments and hierarchies

### Email Template Configuration

1. Configure notification email templates
2. Customize email content and formatting
3. Set up automatic email triggers
4. Configure escalation email procedures

### User Permissions

1. Assign approval permissions to users
2. Configure approval limits for each user
3. Set up approval delegation rules
4. Define backup approver assignments

## Usage

### Purchase Order Approval Process

1. Create purchase orders as usual
2. System automatically determines required approval levels
3. Purchase orders are routed to appropriate approvers
4. Approvers receive email notifications for pending approvals

### Approval Management

1. Access approval dashboard to view pending approvals
2. Review purchase order details and supporting documents
3. Approve or reject purchase orders with comments
4. Track approval status and history

### Delegation Management

1. Set up temporary approval delegations
2. Configure delegation periods and scope
3. Monitor delegation status and activity
4. Revert delegations when needed

### Approval Monitoring

1. Monitor approval workflow performance
2. Track approval times and bottlenecks
3. Generate approval reports and analytics
4. Identify process improvement opportunities

## Technical Details

### Models

* `purchase.approval.level`: Approval level configuration
* Enhanced `purchase.order`: Extended with approval workflow functionality

### Key Features

* Multi-level approval workflow automation
* Amount-based approval rule engine
* Email notification and escalation system
* Complete approval audit trails
* Delegation and backup approver management
* Integration with existing purchase workflows

### Email Templates

* Purchase order approval request notifications
* Approval confirmation emails
* Escalation and reminder notifications
* Delegation notification templates

## Dependencies

* `purchase`: Core purchase functionality
* `purchase_q`: Enhanced purchase management

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

