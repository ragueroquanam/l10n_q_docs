# Account Q Payment from File - Usage Guide

## Overview

This module allows processing customer payments from uploaded files (Excel from Red Pagos or TXT from Abitab). It automatically matches payments to invoices using barcodes and creates the corresponding payment records.

## Installation

1. Install the module dependencies:
   ```bash
   pip install openpyxl
   ```

2. Install the module in Odoo:
   - Go to Apps
   - Search for "Account Q Payment from File"
   - Click Install

## Configuration

### 1. Configure Invoice Barcodes

Before processing payments, you need to add barcode information to your customer invoices:

1. Go to **Accounting > Customers > Invoices**
2. Open a customer invoice
3. Fill in the barcode fields:
   - **File Barcode**: Short barcode (17 characters for Abitab matching)
   - **Full Barcode**: Complete barcode (49 characters for Red Pagos matching)

#### Barcode Structure (49 characters total)

**First Part (24 characters) - File Barcode:**
- PMO (3) - Company code
- Contract Number (7) - Customer contract
- Invoice Number (7) - Invoice number with padding
- Due Date (8) - Format: DDMMYYYY

Example: `PMO0422702453180031122024`

**Second Part (25 characters) - File Barcode Full:**
- Amount (11) - Last 2 digits are decimals
- Currency (1) - 1=UYU, 2=USD
- Quota (2) - Usually 00
- Mora Type (1)
- Document Type (1)
- Account (7) - Usually 0000000
- Check Digit (1)

Example: `000000134002002100000008`

**Complete Barcode:**
`PMO0422702453180031122024000000134002002100000008`

### 2. Configure Payment Journals

Ensure you have payment journals configured:
- Go to **Accounting > Configuration > Journals**
- Configure your bank/cash journals
- Add payment methods to each journal

## Usage

### Step 1: Create a Payment File Record

1. Go to **Accounting > Customers > Payments from File**
2. Click **Create**
3. Fill in the header information:
   - **Payment Journal**: Select the journal for payments
   - **Payment Method**: Select the payment method (filtered by journal)
   - **Payment Date**: Default payment date for all lines
   - **File**: Upload the Excel or TXT file

### Step 2: Process the File

1. Click **Process File** button
2. The system will:
   - Detect file type automatically (Excel or TXT)
   - Parse the file content
   - Create lines for each payment in the file
   - Set line state to "Pending"

### Step 3: Review Lines

1. Go to the **Lines** tab
2. Review each line:
   - Green lines: Successfully processed
   - Red lines: Errors (see error message)
   - Gray lines: Pending processing

3. For error lines:
   - Check the error message
   - Fix the issue (e.g., add missing barcode to invoice)
   - Click the **Reprocess** button on the line

### Step 4: Process Payments

1. Click **Process Payments** button
2. The system will:
   - For each pending line:
     - Find the invoice by barcode
     - Validate the amount
     - Create and post the payment
     - Reconcile with the invoice
   - Set line state to "Processed" or "Error"

3. Review results:
   - Check statistics in the header
   - Review any error lines
   - Click **View Payments** to see all created payments

## File Formats

### Excel (Red Pagos)

Expected columns:
- **FECHA**: Payment date (DD/MM/YYYY)
- **TRACK**: Full barcode (49 characters)
- **MONEDA**: Currency code (UYU, USD, etc.)
- **IMPORTE**: Payment amount
- **MOVIMIENTO**: Transaction reference
- **SUB AGENCIA**: Sub agency code
- **CAJA**: Cashier code

Example:
```
FECHA       TRACK                                              MONEDA  IMPORTE  MOVIMIENTO  SUB AGENCIA  CAJA
07/09/2025  PMO0715710483410030062025000000134002002100000006  U$S     155      2439075717  115          4
```

### TXT (Abitab)

Fixed-width format (76 characters per line):
- Positions 1-3: PMO
- Positions 4-10: Account
- Positions 11-15: Receipt number
- Positions 16-17: 00
- Positions 18-26: Invoice number
- Positions 27-28: 00
- Positions 29-33: Original amount
- Positions 34-35: 00
- Positions 36-44: Mora
- Positions 45-46: 00
- Positions 47-51: Total amount
- Positions 52-53: Decimals
- Position 54: Currency (1=UYU, 2=USD)
- Positions 55-62: Due date (DDMMYYYY)
- Positions 63-65: Agency
- Positions 66-68: Sub agency
- Positions 69-76: Payment date (DDMMYYYY)

Example:
```
PMO1014207103030000000000000111788100000000000111788113009202501202109092025
```

## Common Issues and Solutions

### Issue: "Invoice not found for barcode"

**Solution:**
1. Verify the barcode is correct in the file
2. Check if the invoice has the barcode field filled
3. Ensure the invoice is posted (not draft)
4. For Abitab files: Verify the first 17 characters match the invoice's file_barcode
5. For Red Pagos files: Verify the full 49 characters match the invoice's file_barcode_full

### Issue: "Amount mismatch"

**Solution:**
1. Check the invoice's residual amount
2. Verify the amount in the file
3. Consider currency conversion if different currencies
4. Check for rounding differences (tolerance is 0.01)

### Issue: "Invoice is already paid"

**Solution:**
1. Verify the invoice payment state
2. Check if a payment was already created
3. Remove duplicate lines from the file

## Advanced Features

### Reprocess Error Lines

Individual lines can be reprocessed after fixing issues:
1. Open the payment file record
2. Go to the Lines tab
3. Find the error line
4. Click the **Reprocess** button

### View Related Records

From a line, you can:
- Click **View Invoice** to see the matched invoice
- Click **View Payment** to see the created payment

### Reset to Draft

To start over:
1. Open the payment file record
2. Click **Reset to Draft**
3. This will delete all lines
4. Upload a new file or reprocess

## Integration with Martinelli Web Service

For Martinelli implementation, the web service should populate the barcode fields when creating invoices:

```python
invoice_vals = {
    'partner_id': partner.id,
    'invoice_date': date,
    # ... other fields ...
    'file_barcode': 'PMO0422702453180',  # First 17 chars
    'file_barcode_full': 'PMO0422702453180031122024000000134002002100000008',  # Full 49 chars
}
```

### Barcode Generation Logic

The web service should generate barcodes based on:
1. Company code (PMO)
2. Contract number from customer
3. Invoice number with padding
4. Due date
5. Invoice amount with decimals
6. Currency code
7. Other parameters (mora, doc type, etc.)
8. Calculate check digit

## Notes for Future Enhancements

1. **Amount Validation for Martinelli**: 
   - Implement logic to extract amount from barcode
   - Compare with discount amount if within discount period
   - Use barcode positions to determine which amount to validate

2. **Multiple Invoices per Payment**:
   - Currently supports one invoice per payment line
   - Can be extended to support multiple invoices

3. **Batch Processing**:
   - Add option to process files in batch mode
   - Schedule automatic file processing

4. **Notifications**:
   - Send email notifications when processing is complete
   - Alert users of errors requiring attention

