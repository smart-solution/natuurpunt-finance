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
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class sale_order(osv.osv):
    _inherit = 'sale.order'

#    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
#        if context is None:
#            context = {}
#        data_obj = self.pool.get('wizard.data')
#        invoice_obj = self.pool.get('account.invoice')
#        invoice_line_obj = self.pool.get('account.invoice.line')
#        res = super(sale_order, self).action_invoice_create(cr, uid, ids, grouped=False, states=None, date_invoice=False, context=context)
#        sale_ids = data_obj.search(cr, uid, [('sale_order_id','=', ids[0]),
#                                             ('sale_order_line_id','=',False)], order='distribution_id', context=context)
#        line_ids = data_obj.search(cr, uid, [('sale_order_id','=', ids[0]),
#                                             ('sale_order_line_id','!=',False)], order='distribution_id', context=context)
#        if sale_ids:
#            for wiz_data in data_obj.browse(cr, uid, sale_ids, context=context):
#                vals = {'wiz_invoice_id': res}
#                data_obj.write(cr, uid, sale_ids, vals , context=context)
#    
#        if line_ids:
#            inv_lines = invoice_obj.read(cr, uid, res, ['invoice_line'])
#            if len(inv_lines.get('invoice_line')):
#                for line in invoice_line_obj.browse(cr, uid, inv_lines['invoice_line'], context=context):
#                    wdata_ids = data_obj.search(cr, uid, [('sale_order_id','=', ids[0]),
#                                              ('sale_order_line_id','=', line.sale_order_line_id.id)])
#                    for wid in wdata_ids:
#                        data_obj.write(cr, uid, [wid], {'wiz_invoice_id': res,
#                                                 'wiz_invoice_line_id': line.id})
#        return res

sale_order()



class sale_order_line_delivery(osv.osv_memory):

    _name = "sale.order.line.delivery"

    _columns = {
        'delivered_qty': fields.float('0pleverhoeveelheden', digits_compute= dp.get_precision('Product UoS')),
	'delivered_flag': fields.boolean('Facturatie'),
    }

    def delivery_state_set(self, cr, uid, ids, context=None):
        for wiz in self.browse(cr, uid ,ids):
            self.pool.get('sale.order.line').write(cr, uid, [context['active_id']],
		 {'delivered_qty':wiz.delivered_qty,
		 'delivered_flag':wiz.delivered_flag})
        return True


class sale_order_line(osv.osv):

    _inherit = 'sale.order.line'
    
    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1'),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2'),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3'),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
        'delivered_qty': fields.float('0pleverhoeveelheden', digits_compute= dp.get_precision('Product UoS')),
	'delivered_flag': fields.boolean('Facturatie'),
    }

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
	print "################# _prepare_order context:",context
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))

            if 'use_delivered_qty' in context and context['use_delivered_qty']:
                uosqty = line.delivered_qty


            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
                'analytic_dimension_1_id': line.analytic_dimension_1_id.id,
                'analytic_dimension_2_id': line.analytic_dimension_2_id.id,
                'analytic_dimension_3_id': line.analytic_dimension_3_id.id,
                'analytic_dimension_1_required': line.analytic_dimension_1_required,
                'analytic_dimension_2_required': line.analytic_dimension_2_required,
                'analytic_dimension_3_required': line.analytic_dimension_3_required,
                'sale_order_line_id': line.id
            }

            print "XX############## context:",context

        return res


#    def invoice_line_create(self, cr, uid, ids, context=None):
#        if context is None:
#            context = {}
#            
#        context.update({'src_sale': True})
#
#        create_ids = []
#        sales = set()
#        for line in self.browse(cr, uid, ids, context=context):
#            vals = self._prepare_order_line_invoice_line(cr, uid, line, False, context)
#            if vals:
#                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
#                self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
#                sales.add(line.order_id.id)
#                create_ids.append(inv_id)
#        # Trigger workflow events
#        wf_service = netsvc.LocalService("workflow")
#        for sale_id in sales:
#            wf_service.trg_write(uid, 'sale.order', sale_id, cr)
#        return create_ids
#
#    def create(self, cr, uid, data, context=None):
#        result = super(sale_order_line, self).create(cr, uid, data, context=context)
#        data_obj = self.pool.get('wizard.data')
#        sale_ids = data_obj.search(cr, uid, [('sale_order_id','=', data.get('order_id')),
#                                             ('sale_order_line_id','=',False),
#                                             ('analytic_account_id','!=',False)], context=context)
#        line_ids = data_obj.search(cr, uid, [('sale_order_id','=', data.get('order_id')),
#                                             ('sale_order_line_id','=',False),
#                                             ('analytic_account_id','=',False)], context=context)
#        if sale_ids:
#            for wiz_data in data_obj.browse(cr, uid, sale_ids, context=context):
#                vals = {'distribution_id': wiz_data.distribution_id.id,
#                                              'analytic_account_id': wiz_data.analytic_account_id.id,
#                                              'sale_order_id': data.get('order_id'),
#                                              'sale_order_line_id': result}
#                data_obj.create(cr, uid, vals, context=context)
#
#        if line_ids:
#            for wiz_data in data_obj.browse(cr, uid, line_ids, context=context):
#                 vals = {'distribution_id': wiz_data.distribution_id.id,
#                                              'analytic_account_id': wiz_data.analytic_account_id.id,
#                                              'sale_order_id': data.get('order_id'),
#                                              'sale_order_line_id': result}
#                 data_obj.create(cr, uid, vals, context=context)
#
#        return result
#    
#    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
#        """Prepare the dict of values to create the new invoice line for a
#           sales order line. This method may be overridden to implement custom
#           invoice generation (making sure to call super() to establish
#           a clean extension chain).
#
#           :param browse_record line: sale.order.line record to invoice
#           :param int account_id: optional ID of a G/L account to force
#               (this is used for returning products including service)
#           :return: dict of values to create() the invoice line
#        """
#        res = {}
#        if not line.invoiced:
#            if not account_id:
#                if line.product_id:
#                    account_id = line.product_id.property_account_income.id
#                    if not account_id:
#                        account_id = line.product_id.categ_id.property_account_income_categ.id
#                    if not account_id:
#                        raise osv.except_osv(_('Error!'),
#                                _('Please define income account for this product: "%s" (id:%d).') % \
#                                    (line.product_id.name, line.product_id.id,))
#                else:
#                    prop = self.pool.get('ir.property').get(cr, uid,
#                            'property_account_income_categ', 'product.category',
#                            context=context)
#                    account_id = prop and prop.id or False
#            uosqty = self._get_line_qty(cr, uid, line, context=context)
#            uos_id = self._get_line_uom(cr, uid, line, context=context)
#            pu = 0.0
#            if uosqty:
#                pu = round(line.price_unit * line.product_uom_qty / uosqty,
#                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
#            fpos = line.order_id.fiscal_position or False
#            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
#            if not account_id:
#                raise osv.except_osv(_('Error!'),
#                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
#            res = {
#                'name': line.name,
#                'sequence': line.sequence,
#                'origin': line.order_id.name,
#                'account_id': account_id,
#                'price_unit': pu,
#                'quantity': uosqty,
#                'discount': line.discount,
#                'uos_id': uos_id,
#                'product_id': line.product_id.id or False,
#                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
#                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
#                'sale_order_line_id': line.id
#            }
#
#        return res

sale_order_line()


class sale_order_line_make_invoice(osv.osv_memory):

    _inherit="sale.order.line.make.invoice"

    _columns = {

        'use_delivered_qty': fields.boolean('0pleverhoeveelheden')
    }

    def make_invoices(self, cr, uid, ids, context=None):
        """
             To make invoices.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """
        print "oOOOOO in lines"
        if context is None: context = {}
        res = False
        invoices = {}

    #TODO: merge with sale.py/make_invoice
        def make_invoice(order, lines):
            """
                 To make invoices.

                 @param order:
                 @param lines:

                 @return:

            """
            inv = self._prepare_invoice(cr, uid, order, lines)
            inv_id = self.pool.get('account.invoice').create(cr, uid, inv)
            return inv_id

        sales_order_line_obj = self.pool.get('sale.order.line')
        sales_order_obj = self.pool.get('sale.order')
        wf_service = netsvc.LocalService('workflow')
        wizard = self.browse(cr, uid ,ids)[0]
        for line in sales_order_line_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if (not line.invoiced) and (line.state not in ('draft', 'cancel')):
                if not line.order_id in invoices:
                    invoices[line.order_id] = []
                print "1"
                context['use_delivered_qty'] = wizard.use_delivered_qty
                line_id = sales_order_line_obj.invoice_line_create(cr, uid, [line.id], context=context)
                for lid in line_id:
                    invoices[line.order_id].append(lid)
        for order, il in invoices.items():
            res = make_invoice(order, il)
            cr.execute('INSERT INTO sale_order_invoice_rel \
                    (order_id,invoice_id) values (%s,%s)', (order.id, res))
            flag = True
            data_sale = sales_order_obj.browse(cr, uid, order.id, context=context)
            for line in data_sale.order_line:
                if not line.invoiced:
                    flag = False
                    break
            if flag:
                line.order_id.write({'state': 'done'})
                wf_service.trg_validate(uid, 'sale.order', order.id, 'all_lines', cr)

        if not invoices:
            raise osv.except_osv(_('Warning!'), _('Invoice cannot be created for this Sales Order Line due to one of the following reasons:\n1.The state of this sales order line is either "draft" or "cancel"!\n2.The Sales Order Line is Invoiced!'))
        if context.get('open_invoices', False):
            return self.open_invoices(cr, uid, ids, res, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def open_invoices(self, cr, uid, ids, invoice_ids, context=None):
        """ open a view on one of the given invoice_ids """
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': invoice_ids,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': {'type': 'out_invoice'},
            'type': 'ir.actions.act_window',
        }

sale_order_line_make_invoice()


