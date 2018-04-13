# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today Acespritech Solutions Pvt Ltd
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp.osv.orm import browse_record, browse_null


#class purchase_order(osv.osv):
#    _inherit = 'purchase.order'
#
##    def action_invoice_create(self, cr, uid, ids, context=None):
##        i=0
##        data_obj = self.pool.get('wizard.data')
##        invoice_obj = self.pool.get('account.invoice')
##        res = super(purchase_order, self).action_invoice_create(cr, uid, ids, context=None)
##        pur_ids = data_obj.search(cr, uid, [('purchase_order_id','=', ids[0]),
##                                             ('purchase_order_line_id','=',False)], order='distribution_id', context=context)
##        line_ids = data_obj.search(cr, uid, [('purchase_order_id','=', ids[0]),
##                                             ('purchase_order_line_id','!=',False)], order='distribution_id', context=context)
##        if pur_ids:
##            for wiz_data in data_obj.browse(cr, uid, pur_ids, context=context):
##                vals = {'wiz_invoice_id': res}
##                data_obj.write(cr, uid, pur_ids, vals , context=context)
##
##        if line_ids:
##            dimension_line_min = 0
##            dimension_line_max = 0
##            for wiz_data in data_obj.browse(cr, uid, line_ids, context=context):
##                inv_line = invoice_obj.read(cr, uid, res, ['invoice_line'])
##                if dimension_line_min < len(inv_line['invoice_line']):
##                    inv_line_id = inv_line['invoice_line'][dimension_line_min]
##                    vals = {'wiz_invoice_id': res,
##                            'wiz_invoice_line_id': inv_line_id}
##                    dimension_line_max = 0
##                else:
##                    inv_line_id = inv_line['invoice_line'][dimension_line_max]
##                    vals = {'wiz_invoice_id': res,
##                            'wiz_invoice_line_id': inv_line_id}
##                    dimension_line_min = 0
##                dimension_line_min += 1
##                data_obj.write(cr, uid, [wiz_data.id], vals , context=context)
##        return res
##
#purchase_order()

class purchase_order(osv.osv):

    _inherit = "purchase.order"


    def do_merge(self, cr, uid, ids, context=None):
        """
        To merge similar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new purchase order id

        """
        #TOFIX: merged order line should be unlink
        wf_service = netsvc.LocalService("workflow")
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'move_dest_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

        # Compute what the new orders should contain

        new_orders = {}
        user = self.pool.get('res.users').browse(cr, uid, uid)

        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'draft']:
            order_key = make_key(porder, ('partner_id', 'location_id', 'pricelist_id'))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date_order': porder.date_order,
                    'partner_id': porder.partner_id.id,
                    'dest_address_id': porder.dest_address_id.id,
                    'warehouse_id': porder.warehouse_id.id,
                    'location_id': porder.location_id.id,
                    'pricelist_id': porder.pricelist_id.id,
                    'state': 'draft',
                    'order_line': {},
                    'notes': '%s' % (porder.notes or '',),
                    'fiscal_position': porder.fiscal_position and porder.fiscal_position.id or False,
                })
            else:
                if porder.date_order < order_infos['date_order']:
                    order_infos['date_order'] = porder.date_order
                if porder.notes:
                    order_infos['notes'] = (order_infos['notes'] or '') + ('\n%s' % (porder.notes,))
                if porder.origin:
                    if order_infos['origin'].find(porder.origin) == -1:
                        order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin


            for order_line in porder.order_line:
                line_key = make_key(order_line, ('name', 'date_planned', 'taxes_id', 'price_unit',
                'product_id', 'move_dest_id', 
                'analytic_dimension_1_id', 
                'analytic_dimension_2_id', 
                'analytic_dimension_3_id',
                'analytic_dimension_1_required',
                'analytic_dimension_2_required',
                'analytic_dimension_3_required',
                'requisition_id',
                'requisition_line_id',
                ))
                o_line = order_infos['order_line'].setdefault(line_key, {})

                # append a new "standalone" line
                for field in ('product_qty', 'product_uom'):
                    field_val = getattr(order_line, field)
                    if isinstance(field_val, browse_record):
                        field_val = field_val.id
                    o_line[field] = field_val
                o_line['uom_factor'] = order_line.product_uom and order_line.product_uom.factor or 1.0

        allorders = []
        orders_info = {}
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or []) 
                continue

            # cleanup order line data
            for key, value in order_data['order_line'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            order_data['order_line'] = [(0, 0, value) for value in order_data['order_line'].itervalues()]
    
            # Change sequence
            seq_id = self.pool.get('ir.sequence').search(cr, uid, [('code','=','purchase.order'),('company_id','=',user.company_id.id)])
            print 'SEQ ID:',seq_id
            print 'OLD IDS:',old_ids
            seq = self.pool.get('ir.sequence').browse(cr, uid, seq_id)[0]
            print 'ACT NBR:',seq.number_next_actual
            actual_nbr = seq.number_next_actual
            #po_nbr = seq.number_next_actual - len(old_ids)
            old_pos = self.read(cr, uid, old_ids,['name'],context)
            self.unlink(cr, uid, old_ids)
            print "OLD_POS:",old_pos

            # Search for the smallest PO number
            po_nbr = old_pos[0]['name']
            po_big_nbr = old_pos[0]['name']
            for pos in old_pos:
                if pos['name'] < po_nbr:
                    po_nbr = pos['name']
                if pos['name'] > po_big_nbr:
                    po_big_nbr = pos['name']
            po_nbr = int(po_nbr[7:].lstrip("0"))
            po_big_nbr = long(po_big_nbr[7:].lstrip("0"))
            print 'PO NBR:',po_nbr
            print 'PO BIG NBR:',po_big_nbr

            # If the last po number
            self.pool.get('ir.sequence').write(cr, uid, seq_id, {'number_next':po_nbr})

            # create the new order
            neworder_id = self.create(cr, uid, order_data)
            orders_info.update({neworder_id: old_ids})
            allorders.append(neworder_id)

            if (po_big_nbr + 1) != actual_nbr:
                self.pool.get('ir.sequence').write(cr, uid, seq_id, {'number_next':actual_nbr})
            else:
                self.pool.get('ir.sequence').write(cr, uid, seq_id, {'number_next':actual_nbr - 1}) 

            # make triggers pointing to the old orders point to the new order
#            for old_id in old_ids:
#                wf_service.trg_redirect(uid, 'purchase.order', old_id, neworder_id, cr)
#                wf_service.trg_validate(uid, 'purchase.order', old_id, 'purchase_cancel', cr)

        return orders_info

purchase_order()


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
    }

    def onchange_dimension(self, cr, uid, ids, analytic_dimension_2_id,analytic_dimension_3_id):
        """Check for required dimension"""
        result =  {'value':{}}
        result['value']['analytic_dimension_2_required'] = False
        result['value']['analytic_dimension_3_required'] = False

        def check_dims_mandatory(analytic_account):
            if analytic_account.dimensions_mandatory:
                for dimension in analytic_account.allowed_account_ids:
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                       result['value']['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                       result['value']['analytic_dimension_3_required'] = True

        if analytic_dimension_2_id:
            check_dims_mandatory(self.pool.get('account.analytic.account').browse(cr, uid, analytic_dimension_2_id))
        if analytic_dimension_3_id:
            check_dims_mandatory(self.pool.get('account.analytic.account').browse(cr, uid, analytic_dimension_3_id))
        return result

purchase_order_line()

class purchase_requisition(osv.osv):

    _inherit = "purchase.requisition"

    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
        """
        Create New RFQ for Supplier
        """
        if context is None:
            context = {}
        assert partner_id, 'Supplier should be specified'
        purchase_order = self.pool.get('purchase.order')
        purchase_order_line = self.pool.get('purchase.order.line')
        res_partner = self.pool.get('res.partner')
        fiscal_position = self.pool.get('account.fiscal.position')
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        supplier_pricelist = supplier.property_product_pricelist_purchase or False
        res = {}
        porders = []
        for requisition in self.browse(cr, uid, ids, context=context):
#            if supplier.id in filter(lambda x: x, [rfq.state <> 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
#                 raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            location_id = requisition.warehouse_id.lot_input_id.id
            notes = False
#            if not context['skip_note']:
#                notes = requisition.name + ' - ' + requisition.warehouse_id.name + ' - ' + (requisition.description or "")
            purchase_id = purchase_order.create(cr, uid, {
                        'origin': requisition.name,
                        'partner_id': supplier.id,
                        'pricelist_id': supplier_pricelist.id,
                        'location_id': location_id,
                        'company_id': requisition.company_id.id,
                        'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
                        'requisition_id':requisition.id,
                        #'notes':requisition.description,
#                        'notes': notes,
                        'warehouse_id':requisition.warehouse_id.id ,
            })
            res[requisition.id] = purchase_id
            porders.append(purchase_id)
            for line in requisition.line_ids:
                if 'requisition_lines' not in context or ('requisition_lines' in context and context['requisition_lines'] and line.id in context['requisition_lines']):
                    product = line.product_id
                    seller_price, qty, default_uom_po_id, date_planned = self._seller_details(cr, uid, line, supplier, context=context)
                    taxes_ids = product.supplier_taxes_id
                    taxes = fiscal_position.map_tax(cr, uid, supplier.property_account_position, taxes_ids)
                    line_id = purchase_order_line.create(cr, uid, {
                        'order_id': purchase_id,
                        'name': line.name,
                        'product_qty': qty,
                        'product_id': product.id,
                        'price_unit' : line.product_price_unit,
                        'product_uom': line.product_uom_id.id,
                        #'product_uom': default_uom_po_id,
                        #'price_unit': seller_price,
                        'date_planned': date_planned,
                        'taxes_id': [(6, 0, taxes)],
                        'analytic_dimension_1_id': line.analytic_dimension_1_id and line.analytic_dimension_1_id.id or False,
                        'analytic_dimension_2_id': line.analytic_dimension_2_id and line.analytic_dimension_2_id.id or False,
                        'analytic_dimension_3_id': line.analytic_dimension_3_id and line.analytic_dimension_3_id.id or False,
                        'analytic_dimension_1_required': line.analytic_dimension_1_required,
                        'analytic_dimension_2_required': line.analytic_dimension_2_required,
                        'analytic_dimension_3_required': line.analytic_dimension_3_required,
                        'requisition_id': line.requisition_id.id,
                        'requisition_line_id': line.id,
                    }, context=context)

                    if line_id:
                        self.pool.get('purchase.requisition.line').write(cr, uid, [line.id], {'state':'done'})
    
        return res

class purchase_requisition_line(osv.osv):

    _inherit = 'purchase.requisition.line'

    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
    }

    def onchange_dimension(self, cr, uid, ids, analytic_dimension_2_id,analytic_dimension_3_id):
        """Check for required dimension"""
        result =  {'value':{}}
        result['value']['analytic_dimension_2_required'] = False
        result['value']['analytic_dimension_3_required'] = False

        def check_dims_mandatory(analytic_account):
            if analytic_account.dimensions_mandatory:
                for dimension in analytic_account.allowed_account_ids:
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                       result['value']['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                       result['value']['analytic_dimension_3_required'] = True

        if analytic_dimension_2_id:
            check_dims_mandatory(self.pool.get('account.analytic.account').browse(cr, uid, analytic_dimension_2_id))
        if analytic_dimension_3_id:
            check_dims_mandatory(self.pool.get('account.analytic.account').browse(cr, uid, analytic_dimension_3_id))
        return result

purchase_requisition_line()

#class purchase_line_invoice(osv.osv_memory):
#    _inherit = 'purchase.order.line_invoice'
#
#    def makeInvoices(self, cr, uid, ids, context=None):
#        i=0
#        active_id = context.get('active_id')
#        data_obj = self.pool.get('wizard.data')
#        line_obj = self.pool.get('purchase.order.line')
#        invoice_obj = self.pool.get('account.invoice')
#        line_id = line_obj.browse(cr, uid, active_id, context=context)
#        result = super(purchase_line_invoice, self).makeInvoices(cr, uid, ids, context=context)
#        pur_ids = data_obj.search(cr, uid, [('purchase_order_id','=', line_id.order_id.id),
#                                             ('purchase_order_line_id','=',False)], order='distribution_id', context=context)
#        line_ids = data_obj.search(cr, uid, [('purchase_order_id','=', line_id.order_id.id),
#                                             ('purchase_order_line_id','=',active_id)], order='distribution_id', context=context)
#        result_id = result.get('domain')
#        id = eval(result_id)[0][2][0]
#        if pur_ids:
#            for wiz_data in data_obj.browse(cr, uid, pur_ids, context=context):
#                vals = {'wiz_invoice_id': id}
#                data_obj.write(cr, uid, pur_ids, vals , context=context)
#
#        if line_ids:
#            inv_lines = invoice_obj.read(cr, uid, res, ['invoice_line'])
#            if len(inv_lines.get('invoice_line')):
#                for line in invoice_line_obj.browse(cr, uid, inv_lines['invoice_line'], context=context):
#                    wdata_ids = data_obj.search(cr, uid, [('purchase_order_id','=', ids[0]),
#                                              ('purchase_order_line_id','=', line.sale_order_line_id.id)])
#                    for wid in wdata_ids:
#                        data_obj.write(cr, uid, [wid], {'wiz_invoice_id': res,
#                                                 'wiz_invoice_line_id': line.id})
#        return result
#
#purchase_line_invoice()
