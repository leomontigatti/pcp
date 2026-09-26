#!/usr/bin/env python3
"""Acceptance scenarios against the prototype (see README). Creates real documents; rerun freely."""
import os, sys, xmlrpc.client
from pathlib import Path
for line in (Path(__file__).parent / ".env.proto-secrets").read_text().splitlines():
    if "=" in line and not line.startswith("#"): k, v = line.split("=", 1); os.environ.setdefault(k, v)
url=os.environ['ODOO_URL']; db=os.environ['ODOO_DB']; pw=os.environ['ODOO_ADMIN_PASSWORD']
uid=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common').authenticate(db,'admin',pw,{})
m=xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
def call(model,meth,*a,**k):
    try: return m.execute_kw(db,uid,pw,model,meth,list(a),k)
    except xmlrpc.client.Fault as e:
        if 'cannot marshal None' in e.faultString: return None
        raise
def one(model,dom): r=call(model,'search',dom,limit=1); return r[0] if r else None
def rd(model,ids,fields): return call(model,'read',ids if isinstance(ids,list) else [ids],fields=fields)
def first(x): return x[0] if isinstance(x,list) else x
def invoice_so(so):
    """Invoice a confirmed sale order through the public wizard; returns the invoice id."""
    before=set(rd('sale.order',so,['invoice_ids'])[0]['invoice_ids'])
    wiz=first(call('sale.advance.payment.inv','create',[{'advance_payment_method':'delivered'}],context={'active_model':'sale.order','active_ids':[so],'active_id':so}))
    call('sale.advance.payment.inv','create_invoices',[wiz],context={'active_model':'sale.order','active_ids':[so],'active_id':so})
    after=set(rd('sale.order',so,['invoice_ids'])[0]['invoice_ids']); return (after-before).pop()
wh={w['code']:w for w in call('stock.warehouse','search_read',[],fields=['code','lot_stock_id'])}
prods={p['name']:p['id'] for p in call('product.product','search_read',[['barcode','!=',False]],fields=['name'])}
rivera=one('res.partner',[['name','=','Distribuidora Rivera SRL']]); juana=one('res.partner',[['name','=','Juana Pérez']]); sup=one('res.partner',[['name','=','Papelera del Centro SA']])
jr={j['l10n_ar_afip_pos_number']:j['id'] for j in call('account.journal','search_read',[['type','=','sale']],fields=['l10n_ar_afip_pos_number'])}
locs=[w['lot_stock_id'][0] for w in wh.values()]
arf=[k for k in call('account.move','fields_get') if k.startswith('l10n_ar') or k.startswith('l10n_latam')]
def show_inv(invid):
    r=rd('account.move',invid,['name','state','journal_id','amount_untaxed','amount_total']+arf)[0]
    print("  invoice:",r['name'],r['state'],"|",r['journal_id'][1],"| untaxed",r['amount_untaxed'],"total",r['amount_total'])
    print("  AR:",{k:(v[1] if isinstance(v,list) and len(v)==2 else v) for k,v in r.items() if k in arf and v not in (False,0,0.0,'',[])})

print("== stock on hand (topped up to a baseline on every run)")
for code,qty in [('DEP',500),('LOCC',40),('LOCN',40)]:
    loc=wh[code]['lot_stock_id'][0]
    for name,pid in prods.items():
        q=call('stock.quant','search_read',[['product_id','=',pid],['location_id','=',loc]],fields=['quantity'])
        if not q or q[0]['quantity']<qty:
            qid=q[0]['id'] if q else first(call('stock.quant','create',[{'product_id':pid,'location_id':loc}]))
            call('stock.quant','write',[qid],{'inventory_quantity':qty}); call('stock.quant','action_apply_inventory',[qid])
print("  ",[(x['product_id'][1][:10],x['location_id'][1].split('/')[0],x['quantity']) for x in call('stock.quant','search_read',[['location_id','in',locs]],fields=['product_id','location_id','quantity'])])

print("== 1. Factura A from Depósito: Rivera buys 10 boxes of reams (100 units) on Mayorista -14%")
so=first(call('sale.order','create',[{'partner_id':rivera,'warehouse_id':wh['DEP']['id'],
    'order_line':[[0,0,{'product_id':prods['Resma A4 75g'],'product_uom_qty':100}]]}]))
so_r=rd('sale.order',so,['name','pricelist_id','amount_untaxed','amount_total','order_line'])[0]
line=rd('sale.order.line',so_r['order_line'][0],['price_unit','discount','price_subtotal'])[0]
print("  ",so_r['name'],"pricelist:",so_r['pricelist_id'] and so_r['pricelist_id'][1],"| unit",line['price_unit'],"discount",line['discount'],"subtotal",line['price_subtotal'],"total",so_r['amount_total'])
call('sale.order','action_confirm',[so])
pick=rd('sale.order',so,['picking_ids'])[0]['picking_ids'][0]
print("  delivery:",rd('stock.picking',pick,['state','location_id'])[0])
call('stock.picking','button_validate',[pick]); print("  delivery after validate:",rd('stock.picking',pick,['state'])[0]['state'])
inv=invoice_so(so); call('account.move','action_post',[inv]); show_inv(inv)

print("== 2. Cross-location sale: Juana at Local Centro buys 2 boxes of pens (100) held at Depósito")
so2=first(call('sale.order','create',[{'partner_id':juana,'warehouse_id':wh['DEP']['id'],
    'order_line':[[0,0,{'product_id':prods['Bolígrafo azul'],'product_uom_qty':100}]]}]))
call('sale.order','action_confirm',[so2])
pk2=rd('stock.picking',rd('sale.order',so2,['picking_ids'])[0]['picking_ids'][0],['state','location_id','move_ids'])[0]
mv=rd('stock.move',pk2['move_ids'][0],['quantity','state'])[0]
print("  picking:",pk2['state'],"from",pk2['location_id'][1],"| reserved",mv['quantity'],mv['state'])
q=call('product.product','read',[prods['Bolígrafo azul']],fields=['qty_available','free_qty'],context={'warehouse_id':wh['DEP']['id']})[0]
print("  pens at DEP: on hand",q['qty_available'],"free to use",q['free_qty'])
inv2=invoice_so(so2); call('account.move','write',[inv2],{'journal_id':jr[2]}); call('account.move','action_post',[inv2]); show_inv(inv2)

print("== 3. Supplier bill with IIBB Córdoba perception")
tax_p21=one('account.tax',[['name','=','VAT 21%'],['type_tax_use','=','purchase']]); tax_iibb=one('account.tax',[['name','=','P. IIBB CBA']])
n=len(call('account.move','search',[['move_type','=','in_invoice']]))+123
bill=first(call('account.move','create',[{'move_type':'in_invoice','partner_id':sup,'invoice_date':'2026-09-25',
    'l10n_latam_document_number':f'00001-{n:08d}',
    'invoice_line_ids':[[0,0,{'product_id':prods['Resma A4 75g'],'quantity':100,'price_unit':5000,'tax_ids':[[6,0,[tax_p21,tax_iibb]]]}]]}]))
b=rd('account.move',bill,['l10n_latam_document_type_id','amount_untaxed','amount_tax','amount_total'])[0]
print("  doc type:",b['l10n_latam_document_type_id'] and b['l10n_latam_document_type_id'][1],"| untaxed",b['amount_untaxed'],"tax",b['amount_tax'],"total",b['amount_total'])
print("  tax lines:",[(l['name'],l['balance']) for l in call('account.move.line','search_read',[['move_id','=',bill],['display_type','=','tax']],fields=['name','balance'])])
call('account.move','action_post',[bill]); print("  bill:",rd('account.move',bill,['state','name'])[0])

print("== 4. Replenishment: min/max rule at Local Centro for pens, scheduler creates the two-step transfer from Depósito")
op=one('stock.warehouse.orderpoint',[['product_id','=',prods['Bolígrafo azul']],['warehouse_id','=',wh['LOCC']['id']]])
if not op:
    op=first(call('stock.warehouse.orderpoint','create',[{'product_id':prods['Bolígrafo azul'],'warehouse_id':wh['LOCC']['id'],
        'location_id':wh['LOCC']['lot_stock_id'][0],'product_min_qty':50,'product_max_qty':150,'trigger':'auto'}]))
routes=call('stock.route','search_read',[['supplied_wh_id','=',wh['LOCC']['id']],['supplier_wh_id','=',wh['DEP']['id']]],fields=['name'])
print("  resupply route:",[r['name'] for r in routes])
if routes: call('stock.warehouse.orderpoint','write',[op],{'route_id':routes[0]['id']})
call('stock.warehouse.orderpoint','action_replenish',[op])
pk=call('stock.picking','search_read',[['product_id','=',prods['Bolígrafo azul']],['sale_id','=',False],['picking_type_id.code','in',['internal','outgoing','incoming']],['picking_type_id.name','!=','Consumo interno']],fields=['name','state','origin','location_id','location_dest_id','picking_type_id'],order='id')
for p in pk[-2:]: print("  ",p['name'],p['state'],"| origin",p['origin'],"|",p['location_id'][1],"->",p['location_dest_id'][1],"|",p['picking_type_id'][1])
out=[p for p in pk if p['location_dest_id'][1].split('/')[0] not in ('DEP','LOCC','LOCN')]
if out and out[-1]['state']=='assigned':
    call('stock.picking','button_validate',[out[-1]['id']]); print("  dispatched:",rd('stock.picking',out[-1]['id'],['state'])[0]['state'])
    q=call('product.product','read',[prods['Bolígrafo azul']],fields=['qty_available','incoming_qty'],context={'warehouse_id':wh['LOCC']['id']})[0]
    print("  pens at LOCC while in transit: on hand",q['qty_available'],"incoming",q['incoming_qty'])

print("== 5. Internal consumption: Local Norte uses 5 sleeves of cups")
pt=one('stock.picking.type',[['name','=','Consumo interno'],['warehouse_id','=',wh['LOCN']['id']]])
ptr=rd('stock.picking.type',pt,['default_location_src_id','default_location_dest_id'])[0]
cons=first(call('stock.picking','create',[{'picking_type_id':pt,'location_id':ptr['default_location_src_id'][0],'location_dest_id':ptr['default_location_dest_id'][0],
    'move_ids':[[0,0,{'product_id':prods['Vasos plásticos 180cc x50'],'product_uom_qty':5,'location_id':ptr['default_location_src_id'][0],'location_dest_id':ptr['default_location_dest_id'][0]}]]}]))
call('stock.picking','action_confirm',[cons]); call('stock.picking','action_assign',[cons]); call('stock.picking','button_validate',[cons])
q=call('product.product','read',[prods['Vasos plásticos 180cc x50']],fields=['qty_available'],context={'warehouse_id':wh['LOCN']['id']})[0]
print("  consumption picking:",rd('stock.picking',cons,['name','state'])[0],"| cups at LOCN now:",q['qty_available'])
ml=call('stock.move.line','search_read',[['location_dest_id','=',ptr['default_location_dest_id'][0]]],fields=['product_id','quantity','location_id'])
print("  consumption report:",[(x['product_id'][1][:12],x['quantity'],x['location_id'][1].split('/')[0]) for x in ml])
