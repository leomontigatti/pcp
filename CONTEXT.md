# PCP

ERP implementation for a single Córdoba, Argentina company (one CUIT) that sells stationery, disposable items and related goods, both wholesale and retail, from a warehouse and a few retail stores.

Each term has an English name, used in discussion and in all code identifiers, and a Spanish translation, used only where an end user reads it.

## Language

### Places

**Retail Store**:
A physical store open to the public. Holds its own stock and sells to both **Retail Customers** and **Wholesale Customers** through a **Point of Sale**.
_Spanish_: Local, librería, sucursal
_Avoid_: Salespoint, shop, branch, negocio (in code)

**Point of Sale (POS)**:
The till application a **Retail Store** sells and invoices through. Software, not a place.
_Spanish_: Punto de venta (caja)
_Avoid_: Fiscal printer, till, register

**Warehouse**:
The single central stock location. Receives purchases, fills **Replenishment Requests** and is the only place the **Special List** is used.
_Spanish_: Depósito
_Avoid_: Main store, central

### Customers and prices

**Wholesale Customer**:
A customer assigned a wholesale **Price List** and a **Customer Discount**. Wholesale status belongs to the customer, never to the quantity bought or the location of the sale.
_Spanish_: Cliente mayorista, revendedor
_Avoid_: Bulk buyer, mayorista by volume

**Retail Customer**:
Anyone who buys without being a **Wholesale Customer**; pays the **Retail List** regardless of quantity.
_Spanish_: Cliente minorista, consumidor final
_Avoid_: Walk-in

**Price List**:
A named set of unit prices per **Product**, IVA included. Three exist: the **Retail List**, the **Wholesale List** and the **Special List**.
_Spanish_: Lista de precios
_Avoid_: Tariff, pricing tier

**Retail List**:
The **Price List** every **Retail Customer** pays.
_Spanish_: Lista minorista (lista 2)

**Wholesale List**:
The **Price List** a **Wholesale Customer** is assigned; their **Customer Discount** applies on top of it.
_Spanish_: Lista mayorista (lista 1)

**Special List**:
A **Price List** for very large quantities, used only at the **Warehouse**.
_Spanish_: Lista especial

**Customer Discount**:
A percentage stored on a **Wholesale Customer** and applied by default to every line they buy. A line may override it.
_Spanish_: Descuento del cliente
_Avoid_: Price list per customer, bonificación

**Pack Discount**:
An extra percentage (today 5%) added to the **Customer Discount** on a line sold in closed **Packs**.
_Spanish_: Descuento por bulto cerrado
_Avoid_: Volume discount, quantity break

### Stock

**Product**:
A single item with its own stock count, always kept in the smallest unit the company sells (one ream, one sleeve of cups, never one cup). Bought and sold in any quantity of that unit; carries its own IVA rate.
_Spanish_: Artículo
_Avoid_: SKU, item, variant

**Pack**:
The closed quantity of a **Product** it is bought in and often sold in (a box of 10 reams). A quantity on the Product, not a separate Product; a Pack may carry its own barcode.
_Spanish_: Caja, bulto
_Avoid_: Box product, pack product, unit of measure

**Stock Transfer**:
A movement of stock between two of the company's locations: **Warehouse** to **Retail Store**, or **Retail Store** to **Retail Store**. Two steps: the sender confirms dispatch, the receiver confirms arrival; in between the stock is in transit.
_Spanish_: Transferencia interna, movimiento interno
_Avoid_: Restock, delivery

**Replenishment Request**:
The daily list of **Products** a **Retail Store** asks the **Warehouse** for, filled by a **Stock Transfer** delivered at the end of the day. Entered by the store at first; generated from per-store min/max rules once stock is trusted.
_Spanish_: Pedido al depósito
_Avoid_: Purchase order, requisition

**Internal Consumption**:
Stock the company uses itself (paper, cups, bags) instead of selling. A stock operation to a dedicated consumption location, reportable per store and month; never an inventory adjustment.
_Spanish_: Consumo interno, uso interno
_Avoid_: Waste, shrinkage, loss

**Cross-Location Sale**:
A sale a **Retail Store** invoices for a **Product** it does not hold, fulfilled from the **Warehouse** or another store. Always a sales order, never a POS order: stock is reserved at the source on confirmation and leaves it when handed over. The customer either picks up at the Warehouse or returns to the store once a **Stock Transfer** brings it.
_Spanish_: Venta con retiro en depósito, venta a entregar
_Avoid_: Backorder, drop-ship, negative stock

### Fiscal

**Fiscal Point**:
An ARCA-registered invoice numbering point, the prefix of every invoice number. The **Warehouse** and each **Retail Store** have exactly one. A fiscal concept, not a place. A **Cross-Location Sale** uses the Fiscal Point of the store the customer is in.
_Spanish_: Punto de venta ARCA
_Avoid_: Salespoint, punto de venta (in code), Point of Sale

**Perception**:
A tax amount a supplier adds on top of their invoice to the company (IVA or IIBB), which the company later credits against its own tax.
_Spanish_: Percepción
_Avoid_: Withholding, retention

**Withholding**:
A tax amount a payer (today only card processors) keeps back from a payment to the company, handing a certificate instead of the money.
_Spanish_: Retención
_Avoid_: Perception, fee, commission
