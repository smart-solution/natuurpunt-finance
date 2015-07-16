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

class stock_picking(osv.osv):
    _inherit = 'stock.picking'

    def action_invoice_create(self, cr, uid, ids, journal_id=False, group=False, type='out_invoice', context=None):
        i=0
        data_obj = self.pool.get('wizard.data')
        invoice_obj = self.pool.get('account.invoice')
        res = super(stock_picking, self).action_invoice_create(cr, uid, ids, journal_id, group, type, context=None)
        order_id = self.browse(cr, uid, ids[0], context=context)
        if type == 'out_invoice':
            sale_ids = data_obj.search(cr, uid, [('sale_order_id','=', order_id.sale_id.id),
                                                 ('sale_order_line_id','=',False)], order='distribution_id', context=context)
            line_ids = data_obj.search(cr, uid, [('sale_order_id','=', order_id.sale_id.id),
                                             ('sale_order_line_id','!=',False)], order='distribution_id', context=context)
        if type == 'in_invoice':
            sale_ids = data_obj.search(cr, uid, [('purchase_order_id','=', order_id.purchase_id.id),
                                                 ('purchase_order_line_id','=',False)], order='distribution_id', context=context)
            line_ids = data_obj.search(cr, uid, [('purchase_order_id','=', order_id.purchase_id.id),
                                             ('purchase_order_line_id','!=',False)], order='distribution_id', context=context)
            
        for id in res.values():
            invid = id
        if sale_ids:
            for wiz_data in data_obj.browse(cr, uid, sale_ids, context=context):
                vals = {'wiz_invoice_id': invid}
                data_obj.write(cr, uid, sale_ids, vals , context=context)

        if line_ids:
            for wiz_data in data_obj.browse(cr, uid, line_ids, context=context):
                inv_line = invoice_obj.read(cr, uid, invid, ['invoice_line'])
                if i < len(inv_line['invoice_line']):
                    inv_line_id = inv_line['invoice_line'][i]
                    vals = {'wiz_invoice_id': invid,
                            'wiz_invoice_line_id': inv_line_id}
                    j = -1
                else:
                    inv_line_id = inv_line['invoice_line'][j]
                    vals = {'wiz_invoice_id': invid,
                            'wiz_invoice_line_id': inv_line_id}
                i += 1
                j += 1
                data_obj.write(cr, uid, [wiz_data.id], vals , context=context)
        return res

stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: