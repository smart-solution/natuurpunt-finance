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
from tools.translate import _
import time
from datetime import datetime


class account_journal(osv.osv):
    _inherit = "account.journal"
    _columns = {
        'payment_order_exclude': fields.boolean('Not included in payment order'),
    }

class account_account(osv.osv):
    _inherit = "account.account"
    _columns = {
        'dimension_ids': fields.one2many('account.account.analytic.dimension', 'account_id', 'Analytic Dimension'),
    }

account_account()

class account_account_analytic_dimension(osv.osv):
    _name = 'account.account.analytic.dimension'
    _columns = {
        'account_id': fields.many2one('account.account', 'Account'),
        'dimension_id': fields.many2one('account.analytic.dimension', 'Analytic Dimension'),
        'analytic_account_required': fields.boolean('Analytic Account Required')
    }

account_account_analytic_dimension()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    _columns = {
        'dimension_user_id': fields.many2one('res.users', 'Resp. for analytic assignment'),
    } 

    def copy(self, cr, uid, id, default=None, context=None):
        res = super(account_invoice, self).copy(cr, uid, id, default=default, context=context)
        self.button_reset_taxes(cr, uid, [res], context=context)
        return res

    def default_get(self, cr, uid, fields, context=None):
        """Set invoice date and period"""
        if context is None:
            context = {}
        result = super(account_invoice, self).default_get(cr, uid, fields, context=context)
        result['date_invoice'] = datetime.now().strftime('%Y-%m-%d')
        period = self.pool.get('account.period').find(cr, uid)
        result['period_id'] = period and period[0]
        return result

    def button_reset_taxes(self, cr, uid, ids, context=None):
        if context is None:
            context = {} 
        if not '__copy_data_seen' in context and not 'calc_taxes_done' in context:
            ctx = context.copy()
            ait_obj = self.pool.get('account.invoice.tax')
            for id in ids: 
                cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (id,))
                partner = self.browse(cr, uid, id, context=ctx).partner_id
                if partner.lang:
                    ctx.update({'lang': partner.lang})
                for tax in ait_obj.compute(cr, uid, id, context=ctx).values():
                    inv_tax_id = ait_obj.create(cr, uid, tax)
                    # Clear the dimension records
                    clear_lines = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',tax['invoice_line_id']),('invoice_tax_id','=',inv_tax_id)])
                    self.pool.get('wizard.data').unlink(cr, uid, clear_lines)
                    # Create the dimension records if the accounts matches (non-deductible taxes)
                    line_account = self.pool.get('account.invoice.line').browse(cr, uid, tax['invoice_line_id']).account_id.id
                    if line_account == tax['account_id']:
                        inv_lines = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',tax['invoice_line_id']),
                            ('invoice_tax_id','=',False)])
                        for line in inv_lines:
                            self.pool.get('wizard.data').copy(cr, uid, line, default={'wiz_invoice_id':tax['invoice_id'], 'wiz_invoice_line_id':False, 'invoice_tax_id':inv_tax_id}, context=context)

            # Update the stored value (fields.function), so we write to trigger recompute
            #self.write(cr, uid, ids, {'invoice_line':[]}, context=ctx)
        return True 

    def check_tax_lines(self, cr, uid, inv, compute_taxes, ait_obj):
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id
        if not inv.tax_line:
            for tax in compute_taxes.values():
                ait_obj.create(cr, uid, tax) 
        else:
            tax_key = [] 
            for tax in inv.tax_line:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id, tax.account_analytic_id.id, tax.invoice_line_id.id)
                tax_key.append(key)
                # Remove the added sequence
                if not key in compute_taxes:
                    raise osv.except_osv(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if abs(base - tax.base) > company_currency.rounding:
                    raise osv.except_osv(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if not key in tax_key:
                    raise osv.except_osv(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))

    def action_move_create(self, cr, uid, ids, context=None):
        data_obj = self.pool.get('wizard.data')
        invoice_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')
        move_line_obj = self.pool.get('account.move.line')
        analytic_obj = self.pool.get('account.analytic.line')
           
        if context is None:
            context = {}
        context['calc_taxes_done'] = True

        for invoice in self.browse(cr, uid, ids):
            
            # Check if all required analytic entries are filled
            for line in invoice.invoice_line:
                for dimension in line.account_id.dimension_ids:
                    if dimension.analytic_account_required:
                        recs = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',line.id)])
                        if not recs:
                            raise osv.except_osv(_('Error'),_('A required analytic account is not set for the line %s, the dimension %s'%(line.name,dimension.dimension_id.name)))

            # Check for required dependent dimensions
            for line in invoice.invoice_line:
                dim_recs = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',line.id),('analytic_account_id','!=',False)])
                for dim_rec in self.pool.get('wizard.data').browse(cr, uid, dim_recs):
                    if not dim_rec.analytic_account_id.dimensions_mandatory:
                        continue
                    # Get the required dimensions type
                    required_dims = []
                    for ana_dim in dim_rec.analytic_account_id.allowed_account_ids:
                        required_dims.append(ana_dim.dimension_id.id)
                        required_dims = list(set(required_dims))
                        for rdim in required_dims:
                            dim_check = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',line.id),
                                ('distribution_id','=',rdim),('analytic_account_id','!=',False)])
                            if not dim_check:
                                raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the line %s'%(line.name)))
            
            # Check if the analytic account is in the asset
            for line in invoice.invoice_line:
                if line.asset_id:
                    if line.analytic_dimension_1_id.id != line.asset_id.analytic_dimension_1_id.id and \
                        line.analytic_dimension_1_id.id != False:
                            raise osv.except_osv(_('Error'),_('Analytic accounts for the line %s do not correspond with those as defined for the asset.'%(line.name)))
                    if line.analytic_dimension_2_id.id != line.asset_id.analytic_dimension_2_id.id and \
                        line.analytic_dimension_2_id.id != False:
                            raise osv.except_osv(_('Error'),_('Analytic accounts for the line %s do not correspond with those as defined for the asset.'%(line.name)))
                    if line.analytic_dimension_3_id.id != line.asset_id.analytic_dimension_3_id.id and \
                        line.analytic_dimension_3_id.id != False:
                            raise osv.except_osv(_('Error'),_('Analytic accounts for the line %s do not correspond with those as defined for the asset.'%(line.name)))
                

        # Taking this out of the for-loop so it gets called only once.
        res = super(account_invoice, self).action_move_create(cr, uid, ids, context=context)

        # Rewrite the due date in the account move lines based on the due date of the invoice (to avoid odoo bug that recompute the due date even if it is modified on the invoice)
        for invoice in self.browse(cr, uid, ids):
            if invoice.move_id:
                update_ids = []
                for line in invoice.move_id.line_id:
                    if line.date_maturity:
                        update_ids.append(line.id)
                self.pool.get('account.move.line').write(cr, uid, update_ids, {'date_maturity':invoice.date_due})


        # Restarting the for-loop
        for invoice in self.browse(cr, uid, ids):
            acc_ids = data_obj.search(cr, uid, [('wiz_invoice_id','=', invoice.id),
                                                 ('wiz_invoice_line_id','!=',False),
                                                 ('invoice_tax_id','=',False),
                                                 ('analytic_account_id','!=', False)], order='distribution_id', context=context)
            mv_cnt = 0
            for wiz_data in data_obj.browse(cr, uid, acc_ids, context=context):
                        # Only create analytic line for the allowed dimensions
                        dimensions = []
                        for dim in wiz_data.wiz_invoice_line_id.account_id.dimension_ids:
                            dimensions.append(dim.dimension_id.id)
            
                        if wiz_data.distribution_id.id in dimensions: 
                            inv = wiz_data.wiz_invoice_id
                            inv_line = wiz_data.wiz_invoice_line_id

                            # Set the amount sign
                            if inv.type == 'out_invoice':
                                amount = inv_line.price_subtotal
                            elif inv.type == 'in_invoice':
                                amount = -inv_line.price_subtotal
                            elif inv.type == 'in_refund':
                                amount = inv_line.price_subtotal
                            elif inv.type == 'out_refund':
                                amount = -inv_line.price_subtotal
                            else:
                                raise osv.except_osv(_('Error'),_('Cannot find the amount for an invoice line'))
                            if amount == 0:
                                continue

                            # Find the invoice line move
                            move_ids = self.pool.get('account.move.line').search(cr, uid, [('invoice_line_id','=',inv_line.id)])
                            move_id = False
                            if move_ids:
                                 #move_id = move_ids[mv_cnt]
                                 move_id = move_ids[-1]
                                 move = self.pool.get('account.move.line').browse(cr, uid, move_id)
                                 if move.currency_id:
                                     move_id = move_ids[0]
                            data_obj.write(cr, uid, [wiz_data.id], {'move_line_id':move_id})

#                            vals = {
#                                'name': inv_line.name,
#                                'date': inv.date_invoice,
#                                'account_id': wiz_data.analytic_account_id.id,
#                                'journal_id': inv.journal_id.analytic_journal_id.id or None,
#                                'amount': amount,
#                                'ref': inv.number,
#                                'product_id': inv_line.product_id and inv_line.product_id.id or False,
#                                'unit_amount':inv_line.quantity,
#                                'general_account_id': inv_line.account_id.id,
#                                'move_id': move_id,
#                                'user_id': uid,
#                                'period_id': inv.period_id.id
#                            }
#                            analine_res = analytic_obj.create(cr, uid, vals, context=context)

            # Create anaytic entries for the taxes lines (only for non-deductible taxes)
            tax_ids = data_obj.search(cr, uid, [('wiz_invoice_id','=', invoice.id),
                                                 ('wiz_invoice_line_id','=',False),
                                                 ('invoice_tax_id','!=',False),
                                                 ('analytic_account_id','!=', False)], order='distribution_id', context=context)
            for wiz_tax_data in data_obj.browse(cr, uid, tax_ids, context=context):
                    # Only create analytic line for the allowed dimensions
                    dimensions = []
                    for dim in wiz_tax_data.invoice_tax_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
        
                    if wiz_tax_data.distribution_id.id in dimensions: 
                        tax_inv = wiz_tax_data.wiz_invoice_id
                        tax_line = wiz_tax_data.invoice_tax_id

                        # Set the amount sign
                        if tax_inv.type == 'out_invoice':
                            amount = tax_line.amount
                        elif tax_inv.type == 'in_invoice':
                            amount = -tax_line.amount
                        elif tax_inv.type == 'in_refund':
                            amount = tax_line.amount
                        elif tax_inv.type == 'out_refund':
                            amount = -tax_line.amount
                        else:
                            raise osv.except_osv(_('Error'),_('Cannot find the amount for an invoice tax line'))

                        if amount == 0:
                            continue

                        # Fi#nd the tax line move
                        tax_move_ids = self.pool.get('account.move.line').search(cr, uid, [('invoice_tax_id','=',tax_line.id)])
                        tax_move_id = False
                        if tax_move_ids:
                            tax_move_id = tax_move_ids[0]
                            data_obj.write(cr, uid, [wiz_tax_data.id], {'move_line_id':tax_move_id})

#                        vals = {
#                            'name': tax_line.name,
#                            'date': tax_inv.date_invoice,
#                            'account_id': wiz_tax_data.analytic_account_id.id,
#                            'journal_id': tax_inv.journal_id.analytic_journal_id.id or None,
#                            'amount': amount,
#                            'ref': tax_inv.move_id.name,
#                            'unit_amount':1,
#                            'general_account_id': tax_line.account_id.id,
#                            'move_id': tax_move_id,
#                            'user_id': uid,
#                            'period_id': tax_inv.period_id.id
#                        }
#                        analine_res = analytic_obj.create(cr, uid, vals, context=context)
                


        return True


    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context=context)
        res['invoice_line_id'] = x.get('invoice_line_id', False)
        res['invoice_tax_id'] = x.get('invoice_tax_id', False)
        return res

    def create(self, cr, uid, vals, context=None):
        """Check for wizard data without invoice for purchase approval prob"""
        inv_id =  super(account_invoice, self).create(cr, uid, vals, context=context)
        inv = self.pool.get('account.invoice').browse(cr, uid, inv_id)
        lines = [line.id for line in inv.invoice_line]
        wiz_lines = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','in',lines)])
        self.pool.get('wizard.data').write(cr, uid, wiz_lines, {'wiz_invoice_id':inv_id})
        return inv_id

    def write(self, cr, uid, ids, vals, context=None):
        """ Modify the dimension entry"""
        wiz_data_obj = self.pool.get('wizard.data')
        res = super(account_invoice, self).write(cr, uid, ids, vals, context=context)

        # Check fro dimension user constraint
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_multi_analytic_dimenion_user')], context=context)
        res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
        gp_users = [x.id for x in dim_group.users]
        for mod_field in vals:
            # TODO fix reference
            if uid in gp_users and mod_field not in ('invoice_line','dimension_user_id','reference','state'):
                raise osv.except_osv(_('Error'),_("You can only modify the following: analytic assignment, number plate, employee as well as responsible (tab ‘Other info’)"))

        return res

account_invoice()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
        'sale_order_line_id': fields.many2one('sale.order.line', 'Sales Order Line'),
        'purchase_order_line_id': fields.many2one('purchase.order.line', 'Purchase Order Line'),
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
#        'po_delivery_status': fields.related('purchase_order_line_id', 'delivery_state', type='char', readonly=True, string="Delivery Status"),
    }

    _order = 'id'

    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(account_invoice_line, self).default_get(cr, uid, fields, context=context)

#        result['date_invoice'] = datetime.now().strftime('%Y-%m-%d')

        if 'account_id' in result and result['account_id']:
            account = self.pool.get('account.account').browse(cr, uid, result['account_id'])
            for dimension in account.dimension_ids:
                if dimension.analytic_account_required:
                    if dimension.dimension_id.name == 'Interne Dimensie':
                        result['analytic_dimension_1_required'] = True
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                        result['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                        result['analytic_dimension_3_required'] = True

        # Copy the values of the last created line
        if 'id' in context and context['id']:
            lines = self.pool.get('account.invoice').read(cr, uid, context['id'], ['invoice_line'])['invoice_line']
            if lines:
                line = self.pool.get('account.invoice.line').browse(cr, uid, max(lines))
                result['account_id'] = line.account_id.id
                result['analytic_dimension_1_id'] = line.analytic_dimension_1_id.id
                result['analytic_dimension_2_id'] = line.analytic_dimension_2_id.id
                result['analytic_dimension_3_id'] = line.analytic_dimension_3_id.id
                result['name'] = line.name
                result['product_id'] = line.product_id.id
                result['price_unit'] = line.price_unit
                result['discount'] = line.discount
                result['quantity'] = line.quantity
                result['fleet_id'] = line.fleet_id.id
                result['employee_id'] = line.employee_id.id
                result['uos_id'] = line.uos_id.id
                taxes = []
                for tax in line.invoice_line_tax_id:
                    taxes.append(tax.id)
                result['invoice_line_tax_id'] = [(6,0,taxes)]
        return result

    def onchange_account_id(self, cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id):
        """Check for required dimension"""
        #result = super(account_invoice_line, self).onchange_account_id(cr, uid, ids, product_id, partner_id, inv_type, fposition_id, account_id)
        result =  {'value':{}}
        if account_id:
            account = self.pool.get('account.account').browse(cr, uid, account_id)
            result['value']['analytic_dimension_1_required'] = False
            result['value']['analytic_dimension_2_required'] = False
            result['value']['analytic_dimension_3_required'] = False
            result['value']['fleet_mandatory'] = False
            result['value']['employee_mandatory'] = False
            result['value']['asset_mandatory'] = False

            allowed_dims = []
            for dimension in account.dimension_ids:
                allowed_dims.append(dimension.dimension_id.name)
                if dimension.analytic_account_required:
                    if dimension.dimension_id.name == 'Interne Dimensie':
                        result['value']['analytic_dimension_1_required'] = True
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                        result['value']['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                        result['value']['analytic_dimension_3_required'] = True

            # Check for allowed dimensions and remove accounts from line if needed
            if 'Interne Dimensie' not in allowed_dims:
                result['value']['analytic_dimension_1_id'] = False
            if 'Netwerk Dimensie' not in allowed_dims:
                result['value']['analytic_dimension_2_id'] = False
            if 'Projecten, Contracten, Fondsen' not in allowed_dims:
                result['value']['analytic_dimension_3_id'] = False

            if account.fleet_mandatory:
                result['value']['fleet_mandatory'] = True
            if account.employee_mandatory:
                result['value']['employee_mandatory'] = True
            if account.asset_mandatory:
                result['value']['asset_mandatory'] = True

        return result


    def create(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        result = super(account_invoice_line, self).create(cr, uid, data, context=context)
        inv_line = self.browse(cr, uid, result)
   
        # Check if the dimension is from the right dimension
        if inv_line.analytic_dimension_1_id and inv_line.analytic_dimension_1_id.dimension_id.name != 'Interne Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension for the line %s'%(inv_line.name)))
        if inv_line.analytic_dimension_2_id and inv_line.analytic_dimension_2_id.dimension_id.name != 'Netwerk Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension for the line %s'%(inv_line.name)))
        if inv_line.analytic_dimension_3_id and inv_line.analytic_dimension_3_id.dimension_id.name != 'Projecten, Contracten, Fondsen':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension for the line %s'%(inv_line.name)))

        dims= []
        dims.append(data.get('analytic_dimension_1_id'))
        dims.append(data.get('analytic_dimension_2_id'))
        dims.append(data.get('analytic_dimension_3_id'))
        dims = filter(None, dims)
    
        if 'invoice_id' in data:
            inv = self.pool.get('account.invoice').browse(cr, uid, data['invoice_id'])
    
            for dim in self.pool.get('account.analytic.account').browse(cr, uid, dims):
                dim_data = {
                    'wiz_move_id': inv.move_id.id,
                    'wiz_invoice_id': inv_line.invoice_id.id,
                    'wiz_invoice_line_id': inv_line.id,
                    'distribution_id': dim.dimension_id.id,
                    'analytic_account_id': dim.id,
                }
                data_id = self.pool.get('wizard.data').create(cr, uid, dim_data)
        else:
            for dim in self.pool.get('account.analytic.account').browse(cr, uid, dims):
                dim_data = {
                    'wiz_invoice_line_id': inv_line.id,
                    'distribution_id': dim.dimension_id.id,
                    'analytic_account_id': dim.id,
                }
                data_id = self.pool.get('wizard.data').create(cr, uid, dim_data)
        return result


    def write(self, cr, uid, ids, vals, context=None):
        """ Modify the dimension entry"""
        wiz_data_obj = self.pool.get('wizard.data')
        res = super(account_invoice_line, self).write(cr, uid, ids, vals, context=context)

        # Check fro dimension user constraint
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_multi_analytic_dimenion_user')], context=context)
        res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
        gp_users = [x.id for x in dim_group.users]
        for mod_field in vals:
            # TODO fix reference
            if uid in gp_users and mod_field not in ('analytic_dimension_1_id','analytic_dimension_2_id','analytic_dimension_3_id','fleet_id', 'employee_id', 'reference'):
                raise osv.except_osv(_('Error'),_("You can only modify the following: analytic assignment, number plate, employee as well as responsible (tab ‘Other info’)"))


        for line in self.browse(cr, uid, ids):
            if 'analytic_dimension_1_id' in vals and vals['analytic_dimension_1_id']:
                # Check if the analytic account is from the righ dimension
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_1_id'])

                if acc.dimension_id.name != 'Interne Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension'))

                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                dims1 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims1:
                    # Update the dimension entry
                    wiz_data_obj.write(cr, uid, dims1, {'analytic_account_id':vals['analytic_dimension_1_id']})
                else:
                    # Create the dimension entry
                    wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.invoice_id.move_id.id,
                        'wiz_invoice_id': line.invoice_id.id,
                        'wiz_invoice_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_1_id' in vals and not vals['analytic_dimension_1_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                dims1 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims1)

            if 'analytic_dimension_2_id' in vals and vals['analytic_dimension_2_id']:
                # Check if the analytic account is from the righ dimension
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_2_id'])
                if acc.dimension_id.name != 'Netwerk Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension'))
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                dims2 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims2:
                    wiz_data_obj.write(cr, uid, dims2, {'analytic_account_id':vals['analytic_dimension_2_id']})
                else:
                    wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.invoice_id.move_id.id,
                        'wiz_invoice_id': line.invoice_id.id,
                        'wiz_invoice_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_2_id' in vals and not vals['analytic_dimension_2_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                dims2 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims2)

            if 'analytic_dimension_3_id' in vals and vals['analytic_dimension_3_id']:
                # Check if the analytic account is from the righ dimension
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                if acc.dimension_id.name != 'Projecten, Contracten, Fondsen':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension'))

                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                dims3 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims3:
                    wiz_data_obj.write(cr, uid, dims3, {'analytic_account_id':vals['analytic_dimension_3_id']})
                else:
                    acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                    wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.invoice_id.move_id.id,
                        'wiz_invoice_id': line.invoice_id.id,
                        'wiz_invoice_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_3_id' in vals and not vals['analytic_dimension_3_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                dims3 = wiz_data_obj.search(cr, uid, [('wiz_invoice_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims3)
        return res

    def unlink(self, cr, uid, ids, context=None):
        """Delete the existing dimenson entries"""
        dims = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','in',ids)])
        self.pool.get('wizard.data').unlink(cr, uid, dims)
        return super(account_invoice_line, self).unlink(cr, uid, ids, context=context)

    def move_line_get_item(self, cr, uid, line, context=None):
        return {
            'type':'src',
            'name': line.name.split('\n')[0][:64],
            'price_unit':line.price_unit,
            'quantity':line.quantity,
            'price':line.price_subtotal,
            'account_id':line.account_id.id,
            'product_id':line.product_id.id,
            'uos_id':line.uos_id.id,
            'account_analytic_id':line.account_analytic_id.id,
            'taxes':line.invoice_line_tax_id,
            'invoice_line_id': line.id,
        }

    def onchange_asset(self, cr, uid, ids, asset_id, context=None):
        result = super(account_invoice_line, self).onchange_asset(cr, uid, ids, asset_id, context=context)
        if asset_id:
            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
            result['value']['analytic_dimension_1_id'] = asset.analytic_dimension_1_id.id
            result['value']['analytic_dimension_2_id'] = asset.analytic_dimension_2_id.id
            result['value']['analytic_dimension_3_id'] = asset.analytic_dimension_3_id.id
        return result

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        result = {'value':{}}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            if employee.analytic_account_id:
                result['value']['analytic_dimension_1_id'] = employee.analytic_account_id.id
        return result

account_invoice_line()


class account_move(osv.osv):

    _name = 'account.move'
    _inherit = ['account.move','mail.thread']

    def _check_centralisation(self, cursor, user, ids, context=None):
        """deactivate the constraint"""
        return True


    def post(self, cursor, user, ids, context=None):
        analytic_obj = self.pool.get('account.analytic.line')
        data_obj = self.pool.get('wizard.data')
        for move in self.browse(cursor, user, ids, context=context):

            # Don't try to repost a posted entry
            if move.state == 'posted':
                continue

            # Check if all required analytic entries are filled
            for line in move.line_id:
                for dimension in line.account_id.dimension_ids:
                    if dimension.analytic_account_required:
                        if dimension.dimension_id.sequence == 1 and not line.analytic_dimension_1_id and not line.move_id.journal_id.overrule_mandatory:
                            raise osv.except_osv(_('Error'),_('A required analytic account is not set for the line %s, dimension %s'%(line.name,dimension.dimension_id.name)))
                        if dimension.dimension_id.sequence == 2 and not line.analytic_dimension_2_id and not line.move_id.journal_id.overrule_mandatory:
                            raise osv.except_osv(_('Error'),_('A required analytic account is not set for the line %s, dimension %s'%(line.name,dimension.dimension_id.name)))
                        if dimension.dimension_id.sequence == 3 and not line.analytic_dimension_3_id and not line.move_id.journal_id.overrule_mandatory:
                            raise osv.except_osv(_('Error'),_('A required analytic account is not set for the line %s, dimension %s'%(line.name,dimension.dimension_id.name)))

            # Check if the dimension is from the right dimension
            for line in move.line_id:
                if line.analytic_dimension_1_id and line.analytic_dimension_1_id.dimension_id.sequence != 1:
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension'))
                if line.analytic_dimension_2_id and line.analytic_dimension_2_id.dimension_id.sequence != 2:
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension'))
                if line.analytic_dimension_3_id and line.analytic_dimension_3_id.dimension_id.sequence != 3:
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension'))

            # Check if the dimensions are allowed (for importation of entry lines)
            for line in move.line_id:
                # Get the dimensions
                dim_ids = []
                dim_ids.append(line.analytic_dimension_1_id.id)
                dim_ids.append(line.analytic_dimension_2_id.id)
                dim_ids.append(line.analytic_dimension_3_id.id)
                dim_ids = filter(None, dim_ids)

                # Get all allowed dimensions
                allowed_accounts = []
                for dim_id in dim_ids:
                    allowed_accounts_search = self.pool.get('account.analytic.account').read(cursor, user, dim_id, ['allowed_account_ids'])
                    if 'allowed_account_ids' in allowed_accounts_search:
                        allowed_accounts += allowed_accounts_search['allowed_account_ids']

                if len(dim_ids) == 1:
                    continue

                for dim_id in dim_ids:
                    if dim_id not in allowed_accounts:
                        raise osv.except_osv(_('Error'),_('A non-authorized analytic account is set for the line %s (%s)'%(line.name, dim_id)))


                 
#            # Check for required dependent dimensions
#            for line in move.line_id:
#                dim_recs = self.pool.get('wizard.data').search(cursor, user, [('move_line_id','=',line.id),('analytic_account_id','!=',False)])
#                for dim_rec in self.pool.get('wizard.data').browse(cursor, user, dim_recs):
#                    if not dim_rec.analytic_account_id.dimensions_mandatory:
#                        continue
#                    # Get the required dimensions type
#                    required_dims = []
#                    for ana_dim in dim_rec.analytic_account_id.allowed_account_ids:
#                        required_dims.append(ana_dim.dimension_id.id)
#                        required_dims = list(set(required_dims))
#                        for rdim in required_dims:
#                            dim_check = self.pool.get('wizard.data').search(cursor, user, [('move_line_id','=',line.id),
#                                ('distribution_id','=',rdim),('analytic_account_id','!=',False)])
#                            if not dim_check:
#                                if line.statement_line_id:
#                                    raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the line %s\nStmt Ref: %s'%(line.name,line.statement_line_id.ref)))
#                                raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the line %s'%(line.name)))
#
            result = super(account_move, self).post(cursor, user, [move.id], context=context)
#            result = super(account_move, self).button_validate(cursor, user, [move.id], context=context)

#            acc_ids = data_obj.search(cursor, user, [('wiz_move_id','=', move.id),
#                                                 ('move_line_id','!=',False),
#                                                 ('analytic_account_id','!=', False)], order='distribution_id', context=context)


            for line in move.line_id:

                if line.debit:
                    amount = -line.debit
                elif line.credit:
                    amount = line.credit
                else:
                    continue
#                    raise osv.except_osv(_('Error'),_('Cannot find the amount for account move line %s (%s)'%(str(move.id),move.name)))

                if not line.journal_id.analytic_journal_id:
                    raise osv.except_osv(_('Error'),_('Please assign an analytic journal to this financial journal : %s'%(move.journal_id.name)))

                if line.analytic_dimension_1_id:
                    vals = {
                        'name': line.name,
                        'date': line.date,
                        'account_id': line.analytic_dimension_1_id.id,
                        'journal_id': line.journal_id.analytic_journal_id.id,
                        'amount': amount,
                        'amount_currency': line.amount_currency,
                        'ref': move.name,
                        'product_id': line.product_id and line.product_id.id or False,
                        'unit_amount': line.quantity,
                        'general_account_id': line.account_id.id,
                        'move_id': line.id,
                        'user_id': user,
                        'period_id': move.period_id.id
                    }
                    analytic_obj.create(cursor, user, vals, context=context)

                if line.analytic_dimension_2_id:
                    vals = {
                        'name': line.name,
                        'date': line.date,
                        'account_id': line.analytic_dimension_2_id.id,
                        'journal_id': line.journal_id.analytic_journal_id.id,
                        'amount': amount,
                        'amount_currency': line.amount_currency,
                        'ref': move.name,
                        'product_id': line.product_id and line.product_id.id or False,
                        'unit_amount': line.quantity,
                        'general_account_id': line.account_id.id,
                        'move_id': line.id,
                        'user_id': user,
                        'period_id': move.period_id.id
                    }
                    analytic_obj.create(cursor, user, vals, context=context)

                if line.analytic_dimension_3_id:
                    vals = {
                        'name': line.name,
                        'date': line.date,
                        'account_id': line.analytic_dimension_3_id.id,
                        'journal_id': line.journal_id.analytic_journal_id.id,
                        'amount': amount,
                        'amount_currency': line.amount_currency,
                        'ref': move.name,
                        'product_id': line.product_id and line.product_id.id or False,
                        'unit_amount': line.quantity,
                        'general_account_id': line.account_id.id,
                        'move_id': line.id,
                        'user_id': user,
                        'period_id': move.period_id.id
                    }
                    analytic_obj.create(cursor, user, vals, context=context)


#            for wiz_data in data_obj.browse(cursor, user, acc_ids, context=context):
#
#                    print 'WIZ_DATA:',wiz_data
#                    dimensions = []
#                    for dim in wiz_data.move_line_id.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                    print 'DIMENSIONS:',dimensions
#        
#                    if wiz_data.distribution_id.id in dimensions: 
#                        print 'DISTRIBUTION_ID:',wiz_data.distribution_id.id
#                        line = wiz_data.move_line_id
#                        if line.debit:
#                            amount = -line.debit
#                        elif line.credit:
#                            amount = line.credit
#                        else:
#                            raise osv.except_osv(_('Error'),_('Cannot find the amount for account move line %s (%s)'%(str(move.id),move.name)))
#
#                        if not line.journal_id.analytic_journal_id:
#                            raise osv.except_osv(_('Error'),_('Please assign an analytic journal to this financial journal : %s'%(move.journal_id.name)))
#
#                        vals = {
#                            'name': line.name,
#                            'date': line.date,
#                            'account_id': wiz_data.analytic_account_id.id,
#                            'journal_id': line.journal_id.analytic_journal_id.id,
#                            'amount': amount,
#                            'amount_currency': line.amount_currency,
#                            'ref': move.name,
#                            'product_id': line.product_id and line.product_id.id or False,
#                            'unit_amount': line.quantity,
#                            'general_account_id': line.account_id.id,
#                            'move_id': line.id,
#                            'user_id': user,
#                            'period_id': move.period_id.id
#                        }
#                        analytic_obj.create(cursor, user, vals, context=context)

        return True


    def button_cancel(self, cr, uid, ids, context=None):
        """Delete the analytic entries for cancelled account moves"""
        res =  super(account_move, self).button_cancel(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'modified':True})
        if res:
            for move in self.browse(cr, uid, ids):
                lines = []
                for line in move.line_id:
                    lines.append(line.id)
                if lines:
                    ana_lines = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','in',lines)])
                    self.pool.get('account.analytic.line').unlink(cr, uid ,ana_lines)
        return res

    def open_items(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        view_id = self.pool.get('ir.ui.view').search(cr, uid, [('model','=','account.move.line'),('name','=','view.account.move.line.tree.dimension.inherit')])

        return {
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': view_id[0],
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [('move_id','in',ids)]
        }

    def unlink(self, cr, uid, ids, context=None):
        """Update the existing dimenson entries"""
        if context is None:
            context = {}
        for move in self.browse(cr, uid, ids):
            if move.name != '/' and 'allow_delete' not in context:
                 raise osv.except_osv(_('Error'),_('You cannot delete a journal item with an assigned number'))
        dims = self.pool.get('wizard.data').search(cr, uid, [('wiz_move_id','in',ids)])
        self.pool.get('wizard.data').write(cr, uid, dims, {'move_id':False})
        return super(account_move, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if 'invoice' in context and context['invoice']:
            invoice = context['invoice']
            if invoice.type in ['in_invoice','in_refund'] and invoice.supplier_invoice_number:
                ref = invoice.supplier_invoice_number
            elif invoice.type in ['out_invoice','out_refund'] and invoice.name:
                ref = invoice.name
            else:
                ref = ''

            vals['ref'] = ref
        return super(account_move, self).create(cr, uid, vals, context=context)

account_move()


class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    _columns = {
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line'),
        'invoice_tax_id': fields.many2one('account.invoice.tax', 'Invoice Tax Line'),
        'statement_line_id': fields.many2one('account.bank.statement.line', 'Bank Statement Line'),
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
        'partner_ref': fields.related('partner_id', 'ref', type='char', string='Partner Reference', store=True, readonly=True),
#        'overrule_mandatory': fields.related('move_id', 'journal_id', 'overrule_mandatory', type='boolean', string='Disregard mandatory fields'),
        'move_ref': fields.related('move_id', 'name', type='char', size=64, string='Move Ref'),
    }

    _order = 'invoice_line_id'

    
    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(account_move_line, self).default_get(cr, uid, fields, context=context)
        if 'account_id' in result and result['account_id']:
            account = self.pool.get('account.account').browse(cr, uid, result['account_id'])
            for dimension in account.dimension_ids:
                if dimension.analytic_account_required:
                    if dimension.dimension_id.name == 'Interne Dimensie':
                        result['analytic_dimension_1_required'] = True
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                        result['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                        result['analytic_dimension_3_required'] = True
        return result

    def onchange_asset(self, cr, uid, ids, asset_id, context=None):
        result = super(account_move_line, self).onchange_asset(cr, uid, ids, asset_id, context=context)
        if asset_id:
            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
            result['value']['analytic_dimension_1_id'] = asset.analytic_dimension_1_id.id
            result['value']['analytic_dimension_2_id'] = asset.analytic_dimension_2_id.id
            result['value']['analytic_dimension_3_id'] = asset.analytic_dimension_3_id.id
        return result

    def natuurpunt_account_id_change(self, cr, uid, ids, account_id, partner_id, journal_id, context=None):
        if not account_id:
            return {}
        result =  super(account_move_line, self).natuurpunt_account_id_change( cr, uid, ids, account_id, partner_id, journal_id, context=context)

        journal = self.pool.get('account.journal').browse(cr, uid, journal_id)

        account = self.pool.get('account.account').browse(cr, uid, account_id)
        result['value']['analytic_dimension_1_required'] = False
        result['value']['analytic_dimension_2_required'] = False
        result['value']['analytic_dimension_3_required'] = False
        result['value']['fleet_mandatory'] = False
        result['value']['employee_mandatory'] = False
        result['value']['partner_mandatory'] = False
        result['value']['asset_mandatory'] = False

        allowed_dims = []
        for dimension in account.dimension_ids:
            allowed_dims.append(dimension.dimension_id.name)
            if dimension.analytic_account_required:
                if dimension.dimension_id.name == 'Interne Dimensie':
                    result['value']['analytic_dimension_1_required'] = True
                if dimension.dimension_id.name == 'Netwerk Dimensie':
                    result['value']['analytic_dimension_2_required'] = True
                if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                    result['value']['analytic_dimension_3_required'] = True

        # Check for allowed dimensions and remove accounts from line if needed
        if 'Interne Dimensie' not in allowed_dims:
            result['value']['analytic_dimension_1_id'] = False
        if 'Netwerk Dimensie' not in allowed_dims:
            result['value']['analytic_dimension_2_id'] = False
        if 'Projecten, Contracten, Fondsen' not in allowed_dims:
            result['value']['analytic_dimension_3_id'] = False

        if account.fleet_mandatory and not journal.overrule_mandatory:
            result['value']['fleet_mandatory'] = True
        if account.employee_mandatory and not journal.overrule_mandatory:
            result['value']['employee_mandatory'] = True
        if account.asset_mandatory and not journal.overrule_mandatory:
            result['value']['asset_mandatory'] = True
        if account.partner_mandatory:
            result['value']['partner_mandatory'] = True
        return result

    def create(self, cr, uid, data, context=None):
        # If coming from an invoice line
        inv_id = False
        if 'invoice_line_id' in data and data['invoice_line_id']:
            line = self.pool.get('account.invoice.line').browse(cr, uid, data['invoice_line_id'])
            inv_id = line.invoice_id.id
            data['analytic_dimension_1_id'] = line.analytic_dimension_1_id.id
            data['analytic_dimension_2_id'] = line.analytic_dimension_2_id.id
            data['analytic_dimension_3_id'] = line.analytic_dimension_3_id.id
            return super(account_move_line, self).create(cr, uid, data, context=context)

        # If coming from an invoice tax line
        inv_id = False
        if 'invoice_tax_id' in data and data['invoice_tax_id']:
            tax_line = self.pool.get('account.invoice.tax').browse(cr, uid, data['invoice_tax_id'])
            inv_id = tax_line.invoice_id.id
            dimensions = []
            for dim in tax_line.account_id.dimension_ids:
                dimensions.append(dim.dimension_id.id)
            dim1 = tax_line.invoice_line_id.analytic_dimension_1_id.dimension_id and tax_line.invoice_line_id.analytic_dimension_1_id.dimension_id.id
            dim2 = tax_line.invoice_line_id.analytic_dimension_2_id.dimension_id and tax_line.invoice_line_id.analytic_dimension_2_id.dimension_id.id
            dim3 = tax_line.invoice_line_id.analytic_dimension_3_id.dimension_id and tax_line.invoice_line_id.analytic_dimension_3_id.dimension_id.id

            # Dont copy the dimension for deductible taxes (Tax lines with an account without dimensions defined)
            if tax_line.invoice_id.type in ['in_invoice','out_invoice'] and not tax_line.tax_id.account_collected_id:
                if dim1 in dimensions:
                    data['analytic_dimension_1_id'] = tax_line.invoice_line_id.analytic_dimension_1_id.id
                if dim2 in dimensions:
                    data['analytic_dimension_2_id'] = tax_line.invoice_line_id.analytic_dimension_2_id.id
                if dim3 in dimensions:
                    data['analytic_dimension_3_id'] = tax_line.invoice_line_id.analytic_dimension_3_id.id

            if tax_line.invoice_id.type in ['in_refund','out_refund'] and not tax_line.tax_id.account_paid_id:
                if dim1 in dimensions:
                    data['analytic_dimension_1_id'] = tax_line.invoice_line_id.analytic_dimension_1_id.id
                if dim2 in dimensions:
                    data['analytic_dimension_2_id'] = tax_line.invoice_line_id.analytic_dimension_2_id.id
                if dim3 in dimensions:
                    data['analytic_dimension_3_id'] = tax_line.invoice_line_id.analytic_dimension_3_id.id

            if tax_line.account_id == tax_line.invoice_line_id.account_id and tax_line.invoice_line_id.asset_id:
                data['asset_id'] = tax_line.invoice_line_id.asset_id.id
            if tax_line.account_id == tax_line.invoice_line_id.account_id and tax_line.invoice_line_id.employee_id:
                data['employee_id'] = tax_line.invoice_line_id.employee_id.id
            if tax_line.account_id == tax_line.invoice_line_id.account_id and tax_line.invoice_line_id.fleet_id:
                data['fleet_id'] = tax_line.invoice_line_id.fleet_id.id

            return super(account_move_line, self).create(cr, uid, data, context=context)

        # If coming from a bank statement
        if 'statement_line_id' in data and data['statement_line_id']:
            line = self.pool.get('account.bank.statement.line').browse(cr, uid, data['statement_line_id'])
            statement_id = line.statement_id.id
            data['analytic_dimension_1_id'] = line.analytic_dimension_1_id.id
            data['analytic_dimension_2_id'] = line.analytic_dimension_2_id.id
            data['analytic_dimension_3_id'] = line.analytic_dimension_3_id.id
            return super(account_move_line, self).create(cr, uid, data, context=context)

        result = super(account_move_line, self).create(cr, uid, data, context=context)

        line = self.browse(cr, uid, result)
   
        # Check if the dimension is from the right dimension
        if line.analytic_dimension_1_id and line.analytic_dimension_1_id.dimension_id.name != 'Interne Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension for the line %s'%(line.name)))
        if line.analytic_dimension_2_id and line.analytic_dimension_2_id.dimension_id.name != 'Netwerk Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension for the line %s'%(line.name)))
        if line.analytic_dimension_3_id and line.analytic_dimension_3_id.dimension_id.name != 'Projecten, Contracten, Fondsen':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension for the line %s'%(line.name)))

        dims= []
        dims.append(data.get('analytic_dimension_1_id'))
        dims.append(data.get('analytic_dimension_2_id'))
        dims.append(data.get('analytic_dimension_3_id'))
        dims = filter(None, dims)
    
        move = self.pool.get('account.move').browse(cr, uid, data['move_id'])
    
        for dim in self.pool.get('account.analytic.account').browse(cr, uid, dims):
            dim_data = {
                'wiz_move_id': move.id,
                'move_line_id': result,
                'distribution_id': dim.dimension_id.id,
                'analytic_account_id': dim.id,
            }
            self.pool.get('wizard.data').create(cr, uid, dim_data)

        return result


    def write(self, cr, uid, ids, vals, context=None, check=False, update_check=True):
        """ Modify the dimension entry"""

        if context is None:
            context = {}

        # Only finance admin can modify a posted entry
        finance_admin_id = self.pool.get('ir.model.data').get_object(cr, uid, 'account', 'group_account_manager').id
        #finance_admin_id = self.pool.get('ir.model.data').get_object(cr, uid, 'account', 'group_account_user').id
        fin_admin_users = self.pool.get('res.groups').browse(cr, uid, finance_admin_id).users
        user = self.pool.get('res.users').browse(cr, uid, uid)
        for line in self.browse(cr, uid, ids):
#            if line.move_id.state != 'draft'and user not in fin_admin_users:
#                raise osv.except_osv(_('Error'),_("You don't have the right to modify a posted journal item"))
            if line.move_id.state != 'draft' and ('move_id' in vals or 'partner_id' in vals):
                raise osv.except_osv(_('Error'),_("You don't have the right to modify that field in a posted journal item"))
            if line.period_id.fiscalyear_id.analytic_state == "closed" and \
                ('analytic_dimension_1_id' in vals or 'analytic_dimension_2_id' in vals or 'analytic_dimensiin_3_id' in vals):
                    raise osv.except_osv(_('Error'),_("You don't have the right to modify a posted journal item for an analytically closed fiscal year"))
            if line.move_id.state != 'draft' and not line.move_id.modified:
                self.pool.get('account.move').write(cr, uid, [line.move_id.id], {'modified':True})
        

        wiz_data_obj = self.pool.get('wizard.data')
        analytic_obj = self.pool.get('account.analytic.line')
        res = super(account_move_line, self).write(cr, uid, ids, vals=vals, context=context, check=check, update_check=update_check)
        for line in self.browse(cr, uid, ids):
            
            if line.move_id.state == 'draft':
                continue

#            # Check for required dependent dimensions
#            dim_recs = self.pool.get('wizard.data').search(cr, uid, [('move_line_id','=',line.id),('analytic_account_id','!=',False)])
#            for dim_rec in self.pool.get('wizard.data').browse(cr, uid, dim_recs):
#                if not dim_rec.analytic_account_id.dimensions_mandatory:
#                    continue
#                # Get the required dimensions type
#                required_dims = []
#                for ana_dim in dim_rec.analytic_account_id.allowed_account_ids:
#                    required_dims.append(ana_dim.dimension_id.id)
#                    required_dims = list(set(required_dims))
#                    for rdim in required_dims:
#                        dim_check = self.pool.get('wizard.data').search(cr, uid, [('move_line_id','=',line.id),
#                            ('distribution_id','=',rdim),('analytic_account_id','!=',False)])
#                        if not dim_check:
#                            if line.statement_line_id:
#                                raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the line %s\nStmt Ref: %s'%(line.name,line.statement_line_id.ref)))
#                            raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the line %s'%(line.name)))
#
            acc_line = False
            #acc_line = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id)])
            if 'analytic_dimension_1_id' in vals and vals['analytic_dimension_1_id']:
                # Check if the analytic account is from the righ dimension
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                acc_line = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_1_id'])
                if acc.dimension_id.name != 'Interne Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension'))

                if acc_line:
                    # If an analytic entry exists modify it
                    self.pool.get('account.analytic.line').write(cr, uid, acc_line, {'account_id':vals['analytic_dimension_1_id']})
                else:
                    dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                    dims1 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                    if dims1:
                        # Update the dimension entry
                        wiz_data_obj.write(cr, uid, dims1, {'analytic_account_id':vals['analytic_dimension_1_id']})
                    else:
                        # Create the dimension entry
                        acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_1_id'])
                        wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.move_id.id,
                        'move_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                        })

                        vals = {
                            'name': line.name,
                            'date': line.date,
                            'account_id': vals['analytic_dimension_1_id'],
                            'journal_id': line.journal_id.analytic_journal_id.id,
                            'amount': line.credit - line.debit,
                            'amount_currency': line.amount_currency,
                            'ref': line.move_id.name,
                            'product_id': line.product_id and line.product_id.id or False,
                            'unit_amount': line.quantity,
                            'general_account_id': line.account_id.id,
                            'move_id': line.id,
                            'user_id': uid,
                            'period_id': line.move_id.period_id.id
                        }
                        analytic_obj.create(cr, uid, vals, context=context)

            if 'analytic_dimension_1_id' in vals and not vals['analytic_dimension_1_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                acc_line_del = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                self.pool.get('account.analytic.line').unlink(cr, uid, acc_line_del)

                dims1 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims1)

            acc_line = False
            if 'analytic_dimension_2_id' in vals and vals['analytic_dimension_2_id']:
                # Check if the analytic account is from the righ dimension
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                acc_line = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_2_id'])
                if acc.dimension_id.name != 'Netwerk Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension'))

                if acc_line:
                    # If an analytic entry exists modify it
                    self.pool.get('account.analytic.line').write(cr, uid, acc_line, {'account_id':vals['analytic_dimension_2_id']})
                else:
                    dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                    dims2 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                    if dims2:
                        wiz_data_obj.write(cr, uid, dims2, {'analytic_account_id':vals['analytic_dimension_2_id']})
                    else:
                        acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_2_id'])
                        wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.move_id.id,
                        'move_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                        })

                        vals = {
                            'name': line.name,
                            'date': line.date,
                            'account_id': vals['analytic_dimension_2_id'],
                            'journal_id': line.journal_id.analytic_journal_id.id,
                            'amount': line.credit - line.debit,
                            'amount_currency': line.amount_currency,
                            'ref': line.move_id.name,
                            'product_id': line.product_id and line.product_id.id or False,
                            'unit_amount': line.quantity,
                            'general_account_id': line.account_id.id,
                            'move_id': line.id,
                            'user_id': uid,
                            'period_id': line.move_id.period_id.id
                        }
                        analytic_obj.create(cr, uid, vals, context=context)

            if 'analytic_dimension_2_id' in vals and not vals['analytic_dimension_2_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                acc_line_del = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                self.pool.get('account.analytic.line').unlink(cr, uid, acc_line_del)

                dims2 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims2)

            acc_line = False
            if 'analytic_dimension_3_id' in vals and vals['analytic_dimension_3_id']:
                # Check if the analytic account is from the righ dimension
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                acc_line = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                if acc.dimension_id.name != 'Projecten, Contracten, Fondsen':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension'))

                if acc_line:
                    # If an analytic entry exists modify it
                    self.pool.get('account.analytic.line').write(cr, uid, acc_line, {'account_id':vals['analytic_dimension_3_id']})
                else:
                    dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                    dims3 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                    if dims3:
                        wiz_data_obj.write(cr, uid, dims3, {'analytic_account_id':vals['analytic_dimension_3_id']})
                    else:
                        acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                        wiz_data_obj.create(cr, uid, {
                        'wiz_move_id': line.move_id.id,
                        'move_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                        })

                        vals = {
                            'name': line.name,
                            'date': line.date,
                            'account_id': vals['analytic_dimension_3_id'],
                            'journal_id': line.journal_id.analytic_journal_id.id,
                            'amount': line.credit - line.debit,
                            'amount_currency': line.amount_currency,
                            'ref': line.move_id.name,
                            'product_id': line.product_id and line.product_id.id or False,
                            'unit_amount': line.quantity,
                            'general_account_id': line.account_id.id,
                            'move_id': line.id,
                            'user_id': uid,
                            'period_id': line.move_id.period_id.id
                        }
                        analytic_obj.create(cr, uid, vals, context=context)

            if 'analytic_dimension_3_id' in vals and not vals['analytic_dimension_3_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                acc_line_del = self.pool.get('account.analytic.line').search(cr, uid, [('move_id','=',line.id),('dimension_id','in',dimension)])
                self.pool.get('account.analytic.line').unlink(cr, uid, acc_line_del)

                dims3 = wiz_data_obj.search(cr, uid, [('move_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims3)
        return res

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        result = {'value':{}}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            if employee.analytic_account_id:
                result['value']['analytic_dimension_1_id'] = employee.analytic_account_id.id
        return result

account_move_line()


class account_invoice_tax(osv.osv):

    _inherit = 'account.invoice.tax'

    _columns = {
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line'),
        'tax_id': fields.many2one('account.tax', 'Tax'),
    }

    _order = 'invoice_line_id'

    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_tax WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type':'tax',
                'name':t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount'],
                'account_analytic_id': t['account_analytic_id'],
                'invoice_tax_id': t['id']
            })
            self.pool.get('wizard.data').create(cr, uid, {
                    'wiz_invoice_id':invoice_id,
                    'invoice_tax_id':t['id'],
                })
        return res

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        seq = 0
        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, inv.partner_id)['taxes']:
                val={}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])
                val['invoice_line_id'] = line.id

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['tax_id'] = tax['id']
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['tax_id'] = tax['id']
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

#                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'], seq)
                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'], line.id)
                seq+=1

                tax_grouped[key] = val

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped


account_invoice_tax()


class account_bank_statement_line(osv.osv):

    _inherit = 'account.bank.statement.line'

    _columns = {
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
        'partner_ref': fields.related('partner_id', 'ref', type='char', string='Partner Reference', store=True, readonly=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(account_bank_statement_line, self).default_get(cr, uid, fields, context=context)
        if 'account_id' in result and result['account_id']:
            account = self.pool.get('account.account').browse(cr, uid, result['account_id'])
            for dimension in account.dimension_ids:
                if dimension.analytic_account_required:
                    if dimension.dimension_id.name == 'Interne Dimensie':
                        result['analytic_dimension_1_required'] = True
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                        result['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                        result['analytic_dimension_3_required'] = True
        return result

    def onchange_account_id(self, cr, uid, ids, account_id, context=None):
        """Check for required dimension"""
        result = {}
        account = self.pool.get('account.account').browse(cr, uid, account_id)
        result['analytic_dimension_1_required'] = False
        result['analytic_dimension_2_required'] = False
        result['analytic_dimension_3_required'] = False
        result['employee_mandatory'] = False
        result['partner_mandatory'] = False

        if account_id:
            allowed_dims = []
            for dimension in account.dimension_ids:
                allowed_dims.append(dimension.dimension_id.name)
                if dimension.analytic_account_required:
                    if dimension.dimension_id.name == 'Interne Dimensie':
                        result['analytic_dimension_1_required'] = True
                    if dimension.dimension_id.name == 'Netwerk Dimensie':
                        result['analytic_dimension_2_required'] = True
                    if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                        result['analytic_dimension_3_required'] = True

            # Check for allowed dimensions and remove accounts from line if needed
            if 'Interne Dimensie' not in allowed_dims:
                result['analytic_dimension_1_id'] = False
            if 'Netwerk Dimensie' not in allowed_dims:
                result['analytic_dimension_2_id'] = False
            if 'Projecten, Contracten, Fondsen' not in allowed_dims:
                result['analytic_dimension_3_id'] = False

            if account.employee_mandatory:
                result['employee_mandatory'] = True
                result['asset_mandatory'] = True
            if account.partner_mandatory:
                result['partner_mandatory'] = True

        return {'value':result}

    def create(self, cr, uid, data, context=None):
        """Creates the dimension data"""
        result = super(account_bank_statement_line, self).create(cr, uid, data, context=context)

        dims= []
        dims.append(data.get('analytic_dimension_1_id'))
        dims.append(data.get('analytic_dimension_2_id'))
        dims.append(data.get('analytic_dimension_3_id'))
        dims = filter(None, dims)

        line = self.browse(cr, uid, result) 

        # Check if the dimension is from the right dimension
        if line.analytic_dimension_1_id and line.analytic_dimension_1_id.dimension_id.name != 'Interne Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension for the line %s'%(line.name)))
        if line.analytic_dimension_2_id and line.analytic_dimension_2_id.dimension_id.name != 'Netwerk Dimensie':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension for the line %s'%(line.name)))
        if line.analytic_dimension_3_id and line.analytic_dimension_3_id.dimension_id.name != 'Projecten, Contracten, Fondsen':
            raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension for the line %s'%(line.name)))

        for dim in self.pool.get('account.analytic.account').browse(cr, uid, dims):
            dim_data = {
                'statement_id': line.statement_id.id,
                'statement_line_id': line.id,
                'distribution_id': dim.dimension_id.id,
                'analytic_account_id': dim.id,
            }
            self.pool.get('wizard.data').create(cr, uid, dim_data)
        return result 


    def write(self, cr, uid, ids, vals, context=None):
        """ Modify the dimension entry"""
        wiz_data_obj = self.pool.get('wizard.data')
        res = super(account_bank_statement_line, self).write(cr, uid, ids, vals=vals, context=context)
        if type(ids) != type([]):
            ids = [ids]
        for line in self.browse(cr, uid, ids):
            if 'analytic_dimension_1_id' in vals and vals['analytic_dimension_1_id']:
                # Check if the analytic account is from the righ dimension
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_1_id'])
                if acc.dimension_id.name != 'Interne Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 1 is not from the right dimension'))

                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                dims1 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims1:
                    # Update the dimension entry
                    wiz_data_obj.write(cr, uid, dims1, {'analytic_account_id':vals['analytic_dimension_1_id']})
                else:
                    # Create the dimension entry
                    acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_1_id'])
                    wiz_data_obj.create(cr, uid, {
                        'statement_id': line.statement_id.id,
                        'statement_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_1_id' in vals and not vals['analytic_dimension_1_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Interne Dimensie')])
                dims1 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims1)

            if 'analytic_dimension_2_id' in vals and vals['analytic_dimension_2_id']:
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_2_id'])
                if acc.dimension_id.name != 'Netwerk Dimensie':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 2 is not from the right dimension'))

                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                dims2 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims2:
                    wiz_data_obj.write(cr, uid, dims2, {'analytic_account_id':vals['analytic_dimension_2_id']})
                else:
                    acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_2_id'])
                    wiz_data_obj.create(cr, uid, {
                        'statement_id': line.statement_id.id,
                        'statement_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_2_id' in vals and not vals['analytic_dimension_2_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Netwerk Dimensie')])
                dims2 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims2)

            if 'analytic_dimension_3_id' in vals and vals['analytic_dimension_3_id']:
                # Check if the analytic account is from the righ dimension
                acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                if acc.dimension_id.name != 'Projecten, Contracten, Fondsen':
                    raise osv.except_osv(_('Error'),_('The analytic account for dimension 3 is not from the right dimension'))

                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                dims3 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                if dims3:
                    wiz_data_obj.write(cr, uid, dims3, {'analytic_account_id':vals['analytic_dimension_3_id']})
                else:
                    acc = self.pool.get('account.analytic.account').browse(cr, uid, vals['analytic_dimension_3_id'])
                    wiz_data_obj.create(cr, uid, {
                        'statement_id': line.statement_id.id,
                        'statement_line_id': line.id,
                        'distribution_id': acc.dimension_id.id,
                        'analytic_account_id': acc.id or False,
                    })
            if 'analytic_dimension_3_id' in vals and not vals['analytic_dimension_3_id']:
                #If dimesnion removed delete the dimension entry
                dimension = self.pool.get('account.analytic.dimension').search(cr, uid, [('name','=','Projecten, Contracten, Fondsen')])
                dims3 = wiz_data_obj.search(cr, uid, [('statement_line_id','=',line.id),('distribution_id','in',dimension)])
                wiz_data_obj.unlink(cr, uid, dims3)
        return res


    def unlink(self, cr, uid, ids, context=None):
        """Delete the existing dimenson entries"""
        dims = self.pool.get('wizard.data').search(cr, uid, [('statement_line_id','in',ids)])
        self.pool.get('wizard.data').unlink(cr, uid, dims)
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

account_bank_statement_line()


class account_bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def _prepare_bank_move_line(self, cr, uid, st_line, move_id, amount, company_currency_id,context=None):
        """Add the statement_line_id in the account move line"""        
        res = super(account_bank_statement, self)._prepare_bank_move_line(cr, uid, st_line, move_id, amount, company_currency_id, context=context)
        res['statement_line_id'] = st_line.id
        return res

    def button_confirm_bank(self, cr, uid, ids, context=None):
        """Create the anaytic entries for the dimensions"""
        data_obj = self.pool.get('wizard.data')
        statement_obj = self.pool.get('account.statement')
        statement_line_obj = self.pool.get('account.statement.line')
        move_line_obj = self.pool.get('account.move.line')
        analytic_obj = self.pool.get('account.analytic.line')

        for statement in self.browse(cr, uid, ids):
           
            # Check if all required analytic entries are filled
            for line in statement.line_ids:
                for dimension in line.account_id.dimension_ids:
                    if dimension.analytic_account_required:
                        recs = self.pool.get('wizard.data').search(cr, uid, [('statement_line_id','=',line.id)])
                        if not recs:
                            raise osv.except_osv(_('Error'),_('A required analytic account is not set for the dimension %s'%(dimension.dimension_id.name)))

            # Check for required dependent dimensions
            for line in statement.line_ids:
                dim_recs = self.pool.get('wizard.data').search(cr, uid, [('statement_line_id','=',line.id),('analytic_account_id','!=',False)])
                for dim_rec in self.pool.get('wizard.data').browse(cr, uid, dim_recs):
                    if not dim_rec.analytic_account_id.dimensions_mandatory:
                        continue
                    # Get the required dimensions type
                    required_dims = []
                    for ana_dim in dim_rec.analytic_account_id.allowed_account_ids:
                        required_dims.append(ana_dim.dimension_id.id)
                        required_dims = list(set(required_dims))
                        for rdim in required_dims:
                            dim_check = self.pool.get('wizard.data').search(cr, uid, [('statement_line_id','=',line.id),
                                ('distribution_id','=',rdim),('analytic_account_id','!=',False)])
                            if not dim_check:
                                raise osv.except_osv(_('Error'),_('A dependent analytic account is not set for the statement line: %s'%(line.ref)))

                for accdim in line.account_id.dimension_ids:
                    if accdim.dimension_id.sequence == 1 and accdim.analytic_account_required and not line.analytic_dimension_1_id:
                        raise osv.except_osv(_('Error'),_('The analytic account 1 is required but not set for the statement line: %s'%(line.ref)))
                    if accdim.dimension_id.sequence == 2 and accdim.analytic_account_required and not line.analytic_dimension_2_id:
                        raise osv.except_osv(_('Error'),_('The analytic account 2 is required but not set for the statement line: %s'%(line.ref)))
                    if accdim.dimension_id.sequence == 3 and accdim.analytic_account_required and not line.analytic_dimension_3_id:
                        raise osv.except_osv(_('Error'),_('The analytic account 3 is required but not set for the statement line: %s'%(line.ref)))

                if line.account_id.partner_mandatory and not line.partner_id:
                    raise osv.except_osv(_('Error'),_('A required partner is not present on the line %s'%(line.ref)))
                if line.account_id.employee_mandatory and not line.employee_id:
                    raise osv.except_osv(_('Error'),_('A required employee is not present on the line %s'%(line.ref)))

#                if line.account_id.fleet_mandatory and not line.fleet_id:
#                    raise osv.except_osv(_('Error'),_('A required plate number is not present on the line %s'%(line.ref)))
#                if line.account_id.asset_mandatory and not line.asset_id:
#                    raise osv.except_osv(_('Error'),_('A required asset is not present on the line %s'%(line.ref)))

            res = super(account_bank_statement, self).button_confirm_bank(cr, uid, [statement.id], context=context)

            acc_ids = data_obj.search(cr, uid, [('statement_id','=', statement.id),
                                                 ('statement_line_id','!=',False),
                                                 ('analytic_account_id','!=', False)], order='distribution_id', context=context)

            for wiz_data in data_obj.browse(cr, uid, acc_ids, context=context):

                    # Only create analytic line for the allowed dimensions
                    dimensions = []
                    for dim in wiz_data.statement_line_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
        
                    if wiz_data.distribution_id.id in dimensions: 
                        statement = wiz_data.statement_id
                        statement_line = wiz_data.statement_line_id

                        # Find the statement line move
                        move_ids = self.pool.get('account.move.line').search(cr, uid, [('statement_line_id','=',statement_line.id)])
                        move_id = False
                        if move_ids:
                             move_id = move_ids[0]
                        data_obj.write(cr, uid, [wiz_data.id], {'move_line_id':move_id})

#                        vals = {
#                            'name': statement_line.name,
#                            'date': statement_line.date,
#                            'account_id': wiz_data.analytic_account_id.id,
#                            'journal_id': statement.journal_id.analytic_journal_id.id or None,
#                            'amount': statement_line.amount,
#                            'ref': statement_line.name,
#                            'unit_amount': 1,
#                            'general_account_id': statement_line.account_id.id,
#                            'move_id': move_id,
#                            'user_id': uid,
#                            'period_id': statement.period_id.id
#                        }
#                        analine_res = analytic_obj.create(cr, uid, vals, context=context)

        return True

    def button_cancel(self, cr, uid, ids, context=None):
        context.update({'allow_delete':True})
        return super(account_bank_statement, self).button_cancel(cr, uid, ids, context=context)

    def button_statement_lines(self, cr, uid, ids, context=None):
      return {
        'view_type':'form',
        'view_mode':'tree,form',
        'res_model':'account.bank.statement.line',
        'view_id':False,
        'type':'ir.actions.act_window',
        'domain':[('statement_id','in',ids)],
        'context':context,
      }

    def button_journal_entries(self, cr, uid, ids, context=None):
      ctx = (context or {}).copy()
      ctx['journal_id'] = self.browse(cr, uid, ids[0], context=context).journal_id.id
      return {
        'view_type':'form',
        'view_mode':'tree,form',
        'res_model':'account.move.line',
        'view_id':False,
        'type':'ir.actions.act_window',
        'domain':[('statement_id','in',ids)],
        'context':ctx,
      }   

account_bank_statement()

class account_asset_asset(osv.osv):

    _inherit = "account.asset.asset"

    _columns = {
        'account_id': fields.related('category_id', 'account_expense_depreciation_id',  type='many2one', relation="account.account", string='Depreciation Expense Account', store=False, readonly=True),
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1', domain=[('type','!=','view')]),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2', domain=[('type','!=','view')]),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3', domain=[('type','!=','view')]),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
    }    

    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        """Check for required dimension"""
        result = super(account_asset_asset, self).onchange_category_id(cr, uid, ids, category_id, context=context)
        category = self.pool.get('account.asset.category').browse(cr, uid, category_id)
        result['value']['analytic_dimension_1_required'] = False
        result['value']['analytic_dimension_2_required'] = False
        result['value']['analytic_dimension_3_required'] = False
        for dimension in category.account_expense_depreciation_id.dimension_ids:
            if dimension.analytic_account_required:
                if dimension.dimension_id.name == 'Interne Dimensie':
                    result['value']['analytic_dimension_1_required'] = True
                if dimension.dimension_id.name == 'Netwerk Dimensie':
                    result['value']['analytic_dimension_2_required'] = True
                if dimension.dimension_id.name == 'Projecten, Contracten, Fondsen':
                    result['value']['analytic_dimension_3_required'] = True
        result['value']['account_id'] = category.account_expense_depreciation_id.id
        return result

account_asset_asset()

class account_asset_depreciation_line(osv.osv):

    _inherit = 'account.asset.depreciation.line'

    def create_move(self, cr, uid, ids, context=None):
        """Assign analytical dimsnsions to account move lines and rename the account move"""
        move_ids = super(account_asset_depreciation_line, self).create_move(cr, uid, ids, context=context)
        for move in self.pool.get('account.move').browse(cr, uid, move_ids):
            # Rename the journal entry
            self.pool.get('account.move').write(cr, uid, [move.id], {'name':'/'}, context=context)

            # Assign the dimensions
            for line in move.line_id:
                dimensions = {}
                if line.asset_id:
                    dimensions['analytic_dimension_1_id'] = line.asset_id.analytic_dimension_1_id.id
                    dimensions['analytic_dimension_2_id'] = line.asset_id.analytic_dimension_2_id.id
                    dimensions['analytic_dimension_3_id'] = line.asset_id.analytic_dimension_3_id.id
                    self.pool.get('account.move.line').write(cr, uid, [line.id], dimensions, context=context)

            if move.journal_id.entry_posted:
                self.pool.get('account.move').button_validate(cr, uid, [move.id], context=context)
        return move_ids

account_asset_depreciation_line()


class account_fiscalyear(osv.osv):

    _inherit = "account.fiscalyear"

    _columns = {
        'analytic_state': fields.selection([('open','Open'),('closed','Closed')], 'Analytic Status'),
    }

    _defaults = {
        'analytic_state': 'open',
    }
account_fiscalyear()

class hr_employee(osv.osv):

    _inherit = "hr.employee"

    _columns = {
        'reference_nbr': fields.char('Reference Number', size=64),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        res = []
        for employee in self.browse(cr, uid, ids, context=context):
            if employee.reference_nbr:
                name = '[%s] %s'%(employee.reference_nbr, employee.name)
            else:
                name = employee.name
            res.append((employee.id,name))
        return res

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        """  
        Returns a list of tupples containing id, name, as internally it is called {def name_get}
        result format: {[(id, name), (id, name), ...]}

        @param cr: A database cursor
        @param user: ID of the user currently logged in
        @param name: name to search
        @param args: other arguments
        @param operator: default operator is 'ilike', it can be changed
        @param context: context arguments, like lang, time zone
        @param limit: Returns first 'n' ids of complete result, default is 80.

        @return: Returns a list of tupples containing id and name
        """
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('reference_nbr', '=', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context or {})
        return self.name_get(cr, user, ids, context=context)

hr_employee()

class account_move_post(osv.osv_memory):

    _name="account.move.post"

    def account_move_post_entries(self, cr, uid, ids, context=None):
        """Post selected journal entries"""
        if 'active_ids' in context and context['active_ids']:    
            self.pool.get('account.move').button_validate(cr, uid, context['active_ids'], context=context)
        return {'type': 'ir.actions.act_window_close'}

account_move_post()

class payment_order_create(osv.osv_memory):

    _inherit = "payment.order.create"

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Supplier'),
    }

    def extend_payment_order_domain(
            self, cr, uid, payment_order, domain, context=None):
        if payment_order.payment_order_type == 'payment':
            domain += [
                ('account_id.type', 'in', ('payable', 'receivable')),
                ('amount_to_pay', '>', 0)
                ]
        if payment_order.payment_order_type == 'debit':
            domain += [
                ('account_id.type', '=', 'receivable'),
                ('invoice.state', '!=', 'debit_denied'),
                ('amount_to_receive', '>', 0),
                ]
        return True

    def search_entries(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        search_due_date = data.duedate
        search_partner = data.partner_id.id

        payment = self.pool.get('payment.order').browse(
            cr, uid, context['active_id'], context=context)
        # Get the list of approved invoices account move lines
        # Search for move line to pay:
        domain = [('reconcile_id', '=', False), ('move_id.journal_id.payment_order_exclude','=',False), ('move_id.state', '=', 'posted'), ('company_id', '=', payment.mode.company_id.id)]
        self.extend_payment_order_domain(
            cr, uid, payment, domain, context=context)
        domain = domain + ['|', ('date_maturity', '<=', search_due_date), ('date_maturity', '=', False)]

        # If a supplier is specified
        if search_partner:
            domain = domain + [('partner_id', '=', data.partner_id.id)]

        line_ids = line_obj.search(cr, uid, domain, context=context)

        dom_line_ids = []
#        payment_id = self.pool.get('payment.order').browse(cr, uid, payment[0])
        if payment.payment_order_type == 'debit':
            for line in line_obj.browse(cr, uid, line_ids):
                inv_id = self.pool.get('account.invoice').search(cr, uid, [('move_id','=',line.move_id.id)]) 
                # If the move doesnt come from an invoice add it
                if not inv_id:
                    dom_line_ids.append(line.id)
                if inv_id:
                    inv = self.pool.get('account.invoice').browse(cr, uid, inv_id[0])
                    if inv.sdd_mandate_id:
                        dom_line_ids.append(line.id)
        else:
            for line in line_obj.browse(cr, uid, line_ids):
                inv_id = self.pool.get('account.invoice').search(cr, uid, [('move_id','=',line.move_id.id)]) 
                # If the move doesnt come from an invoice add it
                if not inv_id:
                    dom_line_ids.append(line.id)
                if inv_id:
                    # If the invoice is approved
                    inv = self.pool.get('account.invoice').browse(cr, uid, inv_id[0])
                    if inv.state == "approved":
                        dom_line_ids.append(line.id)

        context.update({'line_ids': dom_line_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_create_payment_order_lines')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']

        return {'name': _('Entry Lines'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.order.create',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
        }


class account_move_line_reconcile_find(osv.osv_memory):

    _name = "account.move.line.reconcile.find"

    def neighborhood(self, iterator):
        prev = None 
        for current in iterator:
            yield (prev,current)
            prev = current

    def get_partners_with_debit_credit(self, move_line):
        debit=0.0
        credit=0.0
        for prev,current in self.neighborhood(move_line):
            if prev and prev['partner_id'] != current['partner_id']:
                if debit>0 and credit>0:
                    yield prev['partner_id']
                debit=0.0
                credit=0.0
            debit+=current['debit']
            credit+=current['credit']
        else:
            debit+=current['debit']
            credit+=current['credit']	 
            if debit>0 and credit>0:
	        yield current['partner_id']

    def items_to_reconcile_find(self, cr, uid, ids, context=None):
        """Search for all move lines for partners with debit and credit amount"""
        mod_obj = self.pool.get('ir.model.data')
        line_obj = self.pool.get('account.move.line')

        # Get list of accounts that can be reconciled
        accounts = self.pool.get('account.account').search(cr, uid, [('reconcile','=',True)])
        cr.execute("""
                   select aml.id,aml.partner_id,debit,credit 
                   from account_move_line as aml join account_account as a on a.id = aml.account_id 
                   where reconcile_id is null and partner_id is not null and a.reconcile
                   order by partner_id
                   """)        
        move_lines = cr.dictfetchall()
        #Keep only the partners that have a debit and credit
        line_ids = list(self.get_partners_with_debit_credit(move_lines)) if move_lines else []

        # Find all move lines that could be reconciled
        line_ids = line_obj.search(cr, uid, [('reconcile_id','=',False),('account_id','in',accounts),'|',('partner_id','in',line_ids),('partner_id','=',False)])
#        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_move_line_tree')], context=context)
#        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_move_line_tree')[1]
        except ValueError:
            tree_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'view_move_line_form')[1]
        except ValueError:
            form_view_id = False

        return {'name': _('Journal Items to Reconcile'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move.line',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [('id','in',line_ids)]
        }


class account_move_reconcile(osv.osv):

    _inherit = 'account.move.reconcile'

    def _check_same_partner(self, cr, uid, ids, context=None):
        for reconcile in self.browse(cr, uid, ids, context=context):
            move_lines = [] 
            if not reconcile.opening_reconciliation:
                if reconcile.line_id:
                    first_partner = reconcile.line_id[0].partner_id.id
                    move_lines = reconcile.line_id
                elif reconcile.line_partial_ids:
                    first_partner = reconcile.line_partial_ids[0].partner_id.id
                    move_lines = reconcile.line_partial_ids
                if any([(line.account_id.type in ('receivable', 'payable') and line.partner_id.id != first_partner) for line in move_lines]):
                    raise osv.except_osv(_('Error!'), _('You can only reconcile journal items with the same partner.\n\nThe system tried to reconcile the item:\n%s [%s]\nPartner: %s\nwith\n%s [%s]\nPartner: %s'%(line.name,line.ref,line.partner_id.ref,reconcile.line_id[0].name,reconcile.line_id[0].ref,reconcile.line_id[0].partner_id.ref)))
                    return False
        return True 

    _constraints = [
                    (_check_same_partner, 'You can only reconcile journal items with the same partner.', ['line_id']),
    ]  


class res_parnter(osv.osv):

    _inherit = "res.partner"

    _columns = { 
        'record_id': fields.related('id', type='char', size=64, string='ID'),
    }   


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
