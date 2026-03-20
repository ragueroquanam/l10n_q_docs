# Quanam Batch Payment - CABAL

## Descripción

Módulo para generar archivos de pagos masivos en formato CABAL. 
Soporta dos configuraciones diferentes:

- **CABAL PMSA** (Previsora Martinelli S.A.)
- **CABAL CMSA** (Concesionaria Martinelli S.A.)

## Formato del Archivo

El archivo generado contiene únicamente líneas de detalle (sin encabezado ni línea de cierre).
Cada línea tiene una longitud de 128 caracteres.

### Estructura de cada línea

| Posición | Longitud | Campo | Descripción |
|----------|----------|-------|-------------|
| 1-4 | 4 | Constante | "CBCU" |
| 5-15 | 11 | Número de comercio | PMSA: 28490120004, CMSA: 28437937007 |
| 16 | 1 | Código de moneda | N=Pesos, U=Dólares |
| 17-32 | 16 | Número de tarjeta | Del afiliado |
| 33-41 | 9 | Nro. socio institución | PMSA: Matrícula/Módulo, CMSA: Contrato |
| 42-52 | 11 | Importe a debitar | Con 2 decimales implícitos |
| 53-58 | 6 | Fecha de proceso | DDMMAA |
| 59-62 | 4 | Número de cuota | MMAA |
| 63-74 | 12 | ID Factura | Número de factura |
| 75 | 1 | Aplica devolución IVA | 1=Sí, 0=No |
| 76-90 | 15 | Importe gravado básico | Con 2 decimales implícitos |
| 91-105 | 15 | Importe gravado mínimo | Con 2 decimales implícitos |
| 106-120 | 15 | Importe devolución IVA | Con 2 decimales implícitos |
| 121-128 | 8 | Filler | Espacios |

## Configuración

### CABAL PMSA
- **Número de comercio**: 28490120004
- **Nro. socio institución**: Campo `Matrícula/Módulo` en la factura
- **Número de cuota**: Mes/Año del campo `Fecha de entrega`

### CABAL CMSA
- **Número de comercio**: 28437937007
- **Nro. socio institución**: Campo `Contrato` en la factura
- **Número de cuota**: Mes/Año de la fecha de factura

## Dependencias

- `account_batch_payment_q`

## Instalación

1. Copiar el módulo al directorio de addons
2. Actualizar la lista de aplicaciones en Odoo
3. Instalar el módulo "Quanam Batch Payment - CABAL"

## Uso

1. Ir a Facturación > Pagos > Pagos por lotes
2. Crear un nuevo lote de pagos
3. Seleccionar la configuración "CABAL PMSA" o "CABAL CMSA" según corresponda
4. Agregar los pagos al lote
5. Generar el archivo de pago
