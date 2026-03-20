# Account Q Payment from File

This module allows processing customer payments from uploaded files (Excel or TXT format).

## Features

- Add barcode field to customer invoices
- Upload payment files (Excel from Red Pagos, TXT from Abitab)
- Automatically match payments to invoices using barcodes
- Process payments with configurable journal and payment method
- Track processing status and errors for each line
- Support for Uruguayan payment networks (Red Pagos and Abitab)

## File Formats

### Excel (Red Pagos)
Columns: FECHA, TRACK, MONEDA, IMPORTE, MOVIMIENTO, SUB AGENCIA, CAJA

### TXT (Abitab)
Fixed-width format with specific positions for each field.

## Usage

1. Go to Accounting > Customers > Payments from File
2. Create a new payment file record
3. Select the payment journal and method
4. Upload the file
5. Process the file to create payments

## Configuration

Add barcode information to customer invoices for automatic matching with payment files.

