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

class account_analytic_dimension_distribution(osv.osv):
    _name = 'account.analytic.dimension.distribution'
    _columns = {
        'wizard_link_id': fields.one2many('account.analytic.dimension.distribution.wizard', 'wizard_id', 'Wizard Link ID'),
        'clear_accounts': fields.boolean('Clear Analytic Accounts'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(account_analytic_dimension_distribution, self).default_get(cr, uid, fields, context=context)
        active_id = context.get('active_id')
        active_model = context.get('active_model')
        data_obj = self.pool.get('wizard.data')
        comp_obj = self.pool.get('res.company')
        analytic_obj = self.pool.get('account.analytic.account')
        result = []

        print"ACTIVE MODEL:",active_model

        if active_model == 'sale.order':
            sale_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, sale_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('sale_order_id', '=', active_id),
                                                 ('sale_order_line_id','=',False)], context=context)
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                for line in company.dimension_id:
                    analytic_ids = analytic_obj.search(cr, uid, [('dimension_id','=', line.id)], context=context)
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        if active_model == 'sale.order.line':
            sale_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, sale_line_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('sale_order_line_id', '=', active_id)], context=context)
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                 for line in company.dimension_id:
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        # Purchase Order
        if active_model == 'purchase.order':
            purchase_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, purchase_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('purchase_order_id', '=', active_id),
                                                 ('purchase_order_line_id','=',False)], context=context)
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                for line in company.dimension_id:
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        # Purchase Order Lines
        if active_model == 'purchase.order.line':
            purchase_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, purchase_line_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('purchase_order_line_id', '=', active_id)], context=context)
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                for line in company.dimension_id:
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        # Invoices
        if active_model == 'account.invoice':
            invoice_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, invoice_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('wiz_invoice_id', '=', active_id),
                                                 ('wiz_invoice_line_id','=',False)], context=context)
            #print"========= data ids...", data_ids
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                for line in company.dimension_id:
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        # Account Invoice Lines
        if active_model == 'account.invoice.line':
            invoice_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, invoice_line_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('wiz_invoice_line_id', '=', active_id)], context=context)
            dimensions = []
            analytic_account_required = {}
            #print"========= data ids...", data_ids
            if data_ids:
                #print"data_ids"
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    #print"CONTEXT:",context
                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
                    #print"WIZ DIST:",wizard_value_get.distribution_id.id

                    for dim in wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    

                    if wizard_value_get.distribution_id.id in dimensions: 
                        if 'wizard_link_id' in fields:
                                result.append((0, 0,{
                                        'distribution_id' : wizard_value_get.distribution_id.id,
                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
                                    }))
            else:
                #print"No data ids"
                for line in company.dimension_id:
                    #print"DIMS:",company.dimension_id
                    #print"DIM:",line
                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
                    for dim in invoice_line_obj.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    
                    if line.id in dimensions:
                        if 'wizard_link_id' in fields:
                            result.append((0,0, {
                                        'distribution_id' : line.id,
                                        'analytic_account_id': False,
                                        'analytic_account_required': analytic_account_required[line.id]
                                    }))

        # Account Tax Lines
        if active_model == 'account.invoice.tax':
            invoice_tax_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, invoice_tax_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('invoice_tax_id', '=', active_id)], context=context)
            dimensions = []
            analytic_account_required = {}
            #print"========= data ids...", data_ids
            if data_ids:
                #print"data_ids"
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    #print"CONTEXT:",context
                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
                    #print"WIZ DIST:",wizard_value_get.distribution_id.id

                    for dim in wizard_value_get.invoice_tax_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    

                    if wizard_value_get.distribution_id.id in dimensions: 
                        if 'wizard_link_id' in fields:
                                result.append((0, 0,{
                                        'distribution_id' : wizard_value_get.distribution_id.id,
                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
                                    }))
            else:
                #print"No data ids"
                for line in company.dimension_id:
                    #print"DIMS:",company.dimension_id
                    #print"DIM:",line
                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
                    for dim in invoice_tax_obj.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    
                    if line.id in dimensions:
                        if 'wizard_link_id' in fields:
                            result.append((0,0, {
                                        'distribution_id' : line.id,
                                        'analytic_account_id': False,
                                        'analytic_account_required': analytic_account_required[line.id]
                                    }))
        # Bank Statement lines
        if active_model == 'account.bank.statement.line':
            statement_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, statement_line_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('statement_line_id', '=', active_id)], context=context)
            dimensions = []
            analytic_account_required = {}
            #print"========= data ids...", data_ids
            if data_ids:
                #print"data_ids"
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    #print"CONTEXT:",context
                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
                    #print"WIZ DIST:",wizard_value_get.distribution_id.id

                    for dim in wizard_value_get.statement_line_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    

                    if wizard_value_get.distribution_id.id in dimensions: 
                        if 'wizard_link_id' in fields:
                                result.append((0, 0,{
                                        'distribution_id' : wizard_value_get.distribution_id.id,
                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
                                    }))
            else:
                #print"No data ids"
                for line in company.dimension_id:
                    #print"DIMS:",company.dimension_id
                    #print"DIM:",line
                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
                    for dim in statement_line_obj.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    #print"ACC REQUIRED:",analytic_account_required
                    
                    if line.id in dimensions:
                        if 'wizard_link_id' in fields:
                            result.append((0,0, {
                                        'distribution_id' : line.id,
                                        'analytic_account_id': False,
                                        'analytic_account_required': analytic_account_required[line.id]
                                    }))
        # Account Move
        if active_model == 'account.move':
            #print"in account move"
            invoice_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, invoice_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),
                                                 ('move_line_id','=',False)], context=context)
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
                    if 'wizard_link_id' in fields:
                            result.append((0, 0,{
                                    'distribution_id' : wizard_value_get.distribution_id.id,
                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
                                }))
            else:
                for line in company.dimension_id:
                    if 'wizard_link_id' in fields:
                        result.append((0,0, {
                                    'distribution_id' : line.id,
                                    'analytic_account_id': False,
                                }))

        # Account Move Line
        if active_model == 'account.move.line':
            move_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
            company = comp_obj.browse(cr, uid, move_line_obj.company_id.id, context=context)
            data_ids = data_obj.search(cr, uid, [('move_line_id', '=', active_id)], context=context)
            dimensions = []
            analytic_account_required = {}
            #print"ACTIVE ID:",active_id
            #print"ML DATA IDS:",data_ids
            if data_ids:
                for wizard_value_get in data_obj.browse(cr, uid, data_ids):

                    for dim in wizard_value_get.move_line_id.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                        
                    if wizard_value_get.distribution_id.id in dimensions: 
                        if 'wizard_link_id' in fields:
                                result.append((0, 0,{ 
                                        'distribution_id' : wizard_value_get.distribution_id.id,
                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
                                    })) 

            else:
                for line in company.dimension_id:
                    for dim in move_line_obj.account_id.dimension_ids:
                        dimensions.append(dim.dimension_id.id)
                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
                    #print"DIMENSIONS:",dimensions
                    
                    if line.id in dimensions:
                        if 'wizard_link_id' in fields:
                            result.append((0,0, {
                                        'distribution_id' : line.id,
                                        'analytic_account_id': False,
                                        'analytic_account_required': analytic_account_required[line.id]
                                    }))

        res.update({'wizard_link_id': result})
        #print"WIZARD RES:",res
        return res

    def create_dimension(self, cr, uid, ids, context=None):
        #print"Calling Create Dimenson"
        active_id = context.get('active_id')
        data_obj = self.pool.get('wizard.data')
        active_model = context.get('active_model')
        analytic_obj = self.pool.get('account.analytic.account')
        wizard_data = self.browse(cr, uid, ids[0], context=context)

        for wizard_value in wizard_data.wizard_link_id:
            # Cannot post if a required analytical account is not set
            if not wizard_value.analytic_account_id and wizard_value.analytic_account_required:
                raise osv.except_osv(_('Error'),_('A required analytic account is not set'))


        for wizard_value in wizard_data.wizard_link_id:
            
            print"ACTIVE MODEL:",active_model
            #print"WIZ VAL:",wizard_value
            #print"WIZ VAL ANA ACC:",wizard_value.analytic_account_id.id

            # Sale Orders
            if active_model == 'sale.order':
                sale_data = self.pool.get(active_model).browse(cr, uid, active_id)
                sale_id = data_obj.search(cr, uid, [('sale_order_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                if sale_id:
                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, sale_id, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'sale_order_id': sale_data.id}
                    data_obj.create(cr, uid, vals, context=context)

                    for data in sale_data.order_line:
                        vals = {'distribution_id': wizard_value.distribution_id.id,
                                              'analytic_account_id': wizard_value.analytic_account_id.id,
                                              'sale_order_id': active_id,'sale_order_line_id': data.id}
                        data_obj.create(cr, uid, vals, context=context)

            # Sale Order Lines
            if active_model == 'sale.order.line':
                sale_id = data_obj.search(cr, uid, [('sale_order_line_id', '=', active_id),
                                                ('distribution_id','=', wizard_value.distribution_id.id)], context=context)
                if sale_id:
                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, sale_id, vals, context=context)

            # Purchase Orders
            if active_model == 'purchase.order':
                purchase_data = self.pool.get(active_model).browse(cr, uid, active_id)
                purchase_id = data_obj.search(cr, uid, [('purchase_order_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                if purchase_id:
                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, purchase_id, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'purchase_order_id': purchase_data.id}
                    data_obj.create(cr, uid, vals, context=context)
                    for data in purchase_data.order_line:
                        vals = {'distribution_id': wizard_value.distribution_id.id,
                                              'analytic_account_id': wizard_value.analytic_account_id.id,
                                              'purchase_order_id': active_id,'purchase_order_line_id': data.id}
                        data_obj.create(cr, uid, vals, context=context)

            # Purchase Order Lines
            if active_model == 'purchase.order.line':
                purchase_id = data_obj.search(cr, uid, [('purchase_order_line_id', '=', active_id),
                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                if purchase_id:
                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, purchase_id, vals, context=context)

            # Invoices
            if active_model == 'account.invoice':
                invoice_data = self.pool.get(active_model).browse(cr, uid, active_id)
                invoice_ids = data_obj.search(cr, uid, [('wiz_invoice_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                if invoice_ids:
                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, invoice_ids, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'wiz_invoice_id': invoice_data.id}
                    data_obj.create(cr, uid, vals, context=context)

                    for data in invoice_data.invoice_line:

                        vals = {'distribution_id': wizard_value.distribution_id.id,
                                              'analytic_account_id': wizard_value.analytic_account_id.id,
                                              'wiz_invoice_id': active_id,
                                              'wiz_invoice_line_id': data.id,
                                              }
                        data_obj.create(cr, uid, vals, context=context)

            # Invoice Lines
            if active_model == 'account.invoice.line':
                invoice_line = self.pool.get(active_model).browse(cr, uid, active_id)
                invoice_line_ids = data_obj.search(cr, uid, [('wiz_invoice_line_id', '=', active_id),
                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                #print"INV LINES:",invoice_line_ids
                if invoice_line_ids:
                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, invoice_line_ids, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'wiz_invoice_id': invoice_line.invoice_id.id,
                             'wiz_invoice_line_id': invoice_line.id,
                             }
                    data_obj.create(cr, uid, vals, context=context)

            # Bank Statement Lines
            if active_model == 'account.bank.statement.line':
                statement_line = self.pool.get(active_model).browse(cr, uid, active_id)
                statement_line_ids = data_obj.search(cr, uid, [('statement_line_id', '=', active_id),
                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                print"STATEMENT LINES:",statement_line_ids
                if statement_line_ids:
                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, statement_line_ids, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'statement_id': statement_line.statement_id.id,
                             'statement_line_id': statement_line.id,
                             }
                    data_obj.create(cr, uid, vals, context=context)

            # Account Moves
            if active_model == 'account.move':
                move_data = self.pool.get(active_model).browse(cr, uid, active_id)
                sale_id = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                if sale_id:
                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, sale_id, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'wiz_move_id': move_data.id}
                    data_obj.create(cr, uid, vals, context=context)

                    for data in move_data.line_id:
                        vals = {'distribution_id': wizard_value.distribution_id.id,
                                              'analytic_account_id': wizard_value.analytic_account_id.id,
                                              'wiz_move_id': active_id,'move_line_id': data.id}
                        data_obj.create(cr, uid, vals, context=context)

            # Account Move Lines
            if active_model == 'account.move.line':
                move_line = self.pool.get(active_model).browse(cr, uid, active_id)
                sale_id = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                move_line_ids = data_obj.search(cr, uid, [('move_line_id', '=', active_id),
                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
                #print"MOVE LINE IDS:",move_line_ids
                if move_line_ids:
                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
                    data_obj.write(cr, uid, move_line_ids, vals, context=context)
                else:
                    vals = {'distribution_id': wizard_value.distribution_id.id,
                             'analytic_account_id': wizard_value.analytic_account_id.id,
                             'wiz_move_id': move_line.move_id.id,
                             'move_line_id': move_line.id
                    }
                    data_obj.create(cr, uid, vals, context=context)

        return True

#    def onchange_clear_accounts(self, cr, uid, ids, wizard_link_id, context=None):
#        """clear the account lines from the wizard"""
#        res = {}
#        wiz = []
#        print "IDS:",ids
#        print "CONTEXT:",context
#        print "WLID:",wizard_link_id
#
#    def default_get(self, cr, uid, fields, context=None):
#        if context is None:
#            context = {}
#        res = super(account_analytic_dimension_distribution, self).default_get(cr, uid, fields, context=context)
#        active_id = context.get('active_id')
#        active_model = context.get('active_model')
#        data_obj = self.pool.get('wizard.data')
#        comp_obj = self.pool.get('res.company')
#        analytic_obj = self.pool.get('account.analytic.account')
#        result = []
#
#        print"ACTIVE MODEL:",active_model
#
#        if active_model == 'sale.order':
#            sale_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, sale_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('sale_order_id', '=', active_id),
#                                                 ('sale_order_line_id','=',False)], context=context)
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                for line in company.dimension_id:
#                    analytic_ids = analytic_obj.search(cr, uid, [('dimension_id','=', line.id)], context=context)
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        if active_model == 'sale.order.line':
#            sale_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, sale_line_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('sale_order_line_id', '=', active_id)], context=context)
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                 for line in company.dimension_id:
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        # Purchase Order
#        if active_model == 'purchase.order':
#            purchase_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, purchase_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('purchase_order_id', '=', active_id),
#                                                 ('purchase_order_line_id','=',False)], context=context)
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                for line in company.dimension_id:
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        # Purchase Order Lines
#        if active_model == 'purchase.order.line':
#            purchase_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, purchase_line_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('purchase_order_line_id', '=', active_id)], context=context)
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                for line in company.dimension_id:
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        # Invoices
#        if active_model == 'account.invoice':
#            invoice_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, invoice_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('wiz_invoice_id', '=', active_id),
#                                                 ('wiz_invoice_line_id','=',False)], context=context)
#            #print"========= data ids...", data_ids
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                for line in company.dimension_id:
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        # Account Invoice Lines
#        if active_model == 'account.invoice.line':
#            invoice_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, invoice_line_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('wiz_invoice_line_id', '=', active_id)], context=context)
#            dimensions = []
#            analytic_account_required = {}
#            #print"========= data ids...", data_ids
#            if data_ids:
#                #print"data_ids"
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    #print"CONTEXT:",context
#                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
#                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
#                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
#                    #print"WIZ DIST:",wizard_value_get.distribution_id.id
#
#                    for dim in wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#
#                    if wizard_value_get.distribution_id.id in dimensions: 
#                        if 'wizard_link_id' in fields:
#                                result.append((0, 0,{
#                                        'distribution_id' : wizard_value_get.distribution_id.id,
#                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
#                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
#                                    }))
#            else:
#                #print"No data ids"
#                for line in company.dimension_id:
#                    #print"DIMS:",company.dimension_id
#                    #print"DIM:",line
#                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
#                    for dim in invoice_line_obj.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#                    if line.id in dimensions:
#                        if 'wizard_link_id' in fields:
#                            result.append((0,0, {
#                                        'distribution_id' : line.id,
#                                        'analytic_account_id': False,
#                                        'analytic_account_required': analytic_account_required[line.id]
#                                    }))
#
#        # Account Tax Lines
#        if active_model == 'account.invoice.tax':
#            invoice_tax_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, invoice_tax_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('invoice_tax_id', '=', active_id)], context=context)
#            dimensions = []
#            analytic_account_required = {}
#            #print"========= data ids...", data_ids
#            if data_ids:
#                #print"data_ids"
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    #print"CONTEXT:",context
#                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
#                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
#                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
#                    #print"WIZ DIST:",wizard_value_get.distribution_id.id
#
#                    for dim in wizard_value_get.invoice_tax_id.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#
#                    if wizard_value_get.distribution_id.id in dimensions: 
#                        if 'wizard_link_id' in fields:
#                                result.append((0, 0,{
#                                        'distribution_id' : wizard_value_get.distribution_id.id,
#                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
#                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
#                                    }))
#            else:
#                #print"No data ids"
#                for line in company.dimension_id:
#                    #print"DIMS:",company.dimension_id
#                    #print"DIM:",line
#                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
#                    for dim in invoice_tax_obj.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#                    if line.id in dimensions:
#                        if 'wizard_link_id' in fields:
#                            result.append((0,0, {
#                                        'distribution_id' : line.id,
#                                        'analytic_account_id': False,
#                                        'analytic_account_required': analytic_account_required[line.id]
#                                    }))
#        # Bank Statement lines
#        if active_model == 'account.bank.statement.line':
#            statement_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, statement_line_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('statement_line_id', '=', active_id)], context=context)
#            dimensions = []
#            analytic_account_required = {}
#            #print"========= data ids...", data_ids
#            if data_ids:
#                #print"data_ids"
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    #print"CONTEXT:",context
#                    #print"WIZ VAL GET:",wizard_value_get.wiz_invoice_line_id
#                    #print"WIZ VAL GET ACC:",wizard_value_get.wiz_invoice_line_id.account_id
#                    #print"WIZ VAL GET ACC DIST:",wizard_value_get.wiz_invoice_line_id.account_id.dimension_ids
#                    #print"WIZ DIST:",wizard_value_get.distribution_id.id
#
#                    for dim in wizard_value_get.statement_line_id.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#
#                    if wizard_value_get.distribution_id.id in dimensions: 
#                        if 'wizard_link_id' in fields:
#                                result.append((0, 0,{
#                                        'distribution_id' : wizard_value_get.distribution_id.id,
#                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
#                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
#                                    }))
#            else:
#                #print"No data ids"
#                for line in company.dimension_id:
#                    #print"DIMS:",company.dimension_id
#                    #print"DIM:",line
#                    #print"invoice_line_obj dim:",invoice_line_obj.account_id.dimension_ids
#                    for dim in statement_line_obj.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    #print"ACC REQUIRED:",analytic_account_required
#                    
#                    if line.id in dimensions:
#                        if 'wizard_link_id' in fields:
#                            result.append((0,0, {
#                                        'distribution_id' : line.id,
#                                        'analytic_account_id': False,
#                                        'analytic_account_required': analytic_account_required[line.id]
#                                    }))
#        # Account Move
#        if active_model == 'account.move':
#            #print"in account move"
#            invoice_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, invoice_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),
#                                                 ('move_line_id','=',False)], context=context)
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#                    if 'wizard_link_id' in fields:
#                            result.append((0, 0,{
#                                    'distribution_id' : wizard_value_get.distribution_id.id,
#                                    'analytic_account_id': wizard_value_get.analytic_account_id.id
#                                }))
#            else:
#                for line in company.dimension_id:
#                    if 'wizard_link_id' in fields:
#                        result.append((0,0, {
#                                    'distribution_id' : line.id,
#                                    'analytic_account_id': False,
#                                }))
#
#        # Account Move Line
#        if active_model == 'account.move.line':
#            move_line_obj = self.pool.get(active_model).browse(cr, uid, active_id)
#            company = comp_obj.browse(cr, uid, move_line_obj.company_id.id, context=context)
#            data_ids = data_obj.search(cr, uid, [('move_line_id', '=', active_id)], context=context)
#            dimensions = []
#            analytic_account_required = {}
#            #print"ACTIVE ID:",active_id
#            #print"ML DATA IDS:",data_ids
#            if data_ids:
#                for wizard_value_get in data_obj.browse(cr, uid, data_ids):
#
#                    for dim in wizard_value_get.move_line_id.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                        
#                    if wizard_value_get.distribution_id.id in dimensions: 
#                        if 'wizard_link_id' in fields:
#                                result.append((0, 0,{ 
#                                        'distribution_id' : wizard_value_get.distribution_id.id,
#                                        'analytic_account_id': wizard_value_get.analytic_account_id.id,
#                                        'analytic_account_required': analytic_account_required[wizard_value_get.distribution_id.id]
#                                    })) 
#
#            else:
#                for line in company.dimension_id:
#                    for dim in move_line_obj.account_id.dimension_ids:
#                        dimensions.append(dim.dimension_id.id)
#                        analytic_account_required[dim.dimension_id.id] = dim.analytic_account_required
#                    #print"DIMENSIONS:",dimensions
#                    
#                    if line.id in dimensions:
#                        if 'wizard_link_id' in fields:
#                            result.append((0,0, {
#                                        'distribution_id' : line.id,
#                                        'analytic_account_id': False,
#                                        'analytic_account_required': analytic_account_required[line.id]
#                                    }))
#
#        res.update({'wizard_link_id': result})
#        #print"WIZARD RES:",res
#        return res
#
#    def create_dimension(self, cr, uid, ids, context=None):
#        #print"Calling Create Dimenson"
#        active_id = context.get('active_id')
#        data_obj = self.pool.get('wizard.data')
#        active_model = context.get('active_model')
#        analytic_obj = self.pool.get('account.analytic.account')
#        wizard_data = self.browse(cr, uid, ids[0], context=context)
#
#        for wizard_value in wizard_data.wizard_link_id:
#            # Cannot post if a required analytical account is not set
#            if not wizard_value.analytic_account_id and wizard_value.analytic_account_required:
#                raise osv.except_osv(_('Error'),_('A required analytic account is not set'))
#
#
#        for wizard_value in wizard_data.wizard_link_id:
#            
#            print"ACTIVE MODEL:",active_model
#            #print"WIZ VAL:",wizard_value
#            #print"WIZ VAL ANA ACC:",wizard_value.analytic_account_id.id
#
#            # Sale Orders
#            if active_model == 'sale.order':
#                sale_data = self.pool.get(active_model).browse(cr, uid, active_id)
#                sale_id = data_obj.search(cr, uid, [('sale_order_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                if sale_id:
#                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, sale_id, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'sale_order_id': sale_data.id}
#                    data_obj.create(cr, uid, vals, context=context)
#
#                    for data in sale_data.order_line:
#                        vals = {'distribution_id': wizard_value.distribution_id.id,
#                                              'analytic_account_id': wizard_value.analytic_account_id.id,
#                                              'sale_order_id': active_id,'sale_order_line_id': data.id}
#                        data_obj.create(cr, uid, vals, context=context)
#
#            # Sale Order Lines
#            if active_model == 'sale.order.line':
#                sale_id = data_obj.search(cr, uid, [('sale_order_line_id', '=', active_id),
#                                                ('distribution_id','=', wizard_value.distribution_id.id)], context=context)
#                if sale_id:
#                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, sale_id, vals, context=context)
#
#            # Purchase Orders
#            if active_model == 'purchase.order':
#                purchase_data = self.pool.get(active_model).browse(cr, uid, active_id)
#                purchase_id = data_obj.search(cr, uid, [('purchase_order_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                if purchase_id:
#                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, purchase_id, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'purchase_order_id': purchase_data.id}
#                    data_obj.create(cr, uid, vals, context=context)
#                    for data in purchase_data.order_line:
#                        vals = {'distribution_id': wizard_value.distribution_id.id,
#                                              'analytic_account_id': wizard_value.analytic_account_id.id,
#                                              'purchase_order_id': active_id,'purchase_order_line_id': data.id}
#                        data_obj.create(cr, uid, vals, context=context)
#
#            # Purchase Order Lines
#            if active_model == 'purchase.order.line':
#                purchase_id = data_obj.search(cr, uid, [('purchase_order_line_id', '=', active_id),
#                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                if purchase_id:
#                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, purchase_id, vals, context=context)
#
#            # Invoices
#            if active_model == 'account.invoice':
#                invoice_data = self.pool.get(active_model).browse(cr, uid, active_id)
#                invoice_ids = data_obj.search(cr, uid, [('wiz_invoice_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                if invoice_ids:
#                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, invoice_ids, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'wiz_invoice_id': invoice_data.id}
#                    data_obj.create(cr, uid, vals, context=context)
#
#                    for data in invoice_data.invoice_line:
#
#                        vals = {'distribution_id': wizard_value.distribution_id.id,
#                                              'analytic_account_id': wizard_value.analytic_account_id.id,
#                                              'wiz_invoice_id': active_id,
#                                              'wiz_invoice_line_id': data.id,
#                                              }
#                        data_obj.create(cr, uid, vals, context=context)
#
#            # Invoice Lines
#            if active_model == 'account.invoice.line':
#                invoice_line = self.pool.get(active_model).browse(cr, uid, active_id)
#                invoice_line_ids = data_obj.search(cr, uid, [('wiz_invoice_line_id', '=', active_id),
#                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                #print"INV LINES:",invoice_line_ids
#                if invoice_line_ids:
#                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, invoice_line_ids, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'wiz_invoice_id': invoice_line.invoice_id.id,
#                             'wiz_invoice_line_id': invoice_line.id,
#                             }
#                    data_obj.create(cr, uid, vals, context=context)
#
#            # Bank Statement Lines
#            if active_model == 'account.bank.statement.line':
#                statement_line = self.pool.get(active_model).browse(cr, uid, active_id)
#                statement_line_ids = data_obj.search(cr, uid, [('statement_line_id', '=', active_id),
#                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                print"STATEMENT LINES:",statement_line_ids
#                if statement_line_ids:
#                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, statement_line_ids, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'statement_id': statement_line.statement_id.id,
#                             'statement_line_id': statement_line.id,
#                             }
#                    data_obj.create(cr, uid, vals, context=context)
#
#            # Account Moves
#            if active_model == 'account.move':
#                move_data = self.pool.get(active_model).browse(cr, uid, active_id)
#                sale_id = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                if sale_id:
#                    vals = {'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, sale_id, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'wiz_move_id': move_data.id}
#                    data_obj.create(cr, uid, vals, context=context)
#
#                    for data in move_data.line_id:
#                        vals = {'distribution_id': wizard_value.distribution_id.id,
#                                              'analytic_account_id': wizard_value.analytic_account_id.id,
#                                              'wiz_move_id': active_id,'move_line_id': data.id}
#                        data_obj.create(cr, uid, vals, context=context)
#
#            # Account Move Lines
#            if active_model == 'account.move.line':
#                move_line = self.pool.get(active_model).browse(cr, uid, active_id)
#                sale_id = data_obj.search(cr, uid, [('wiz_move_id', '=', active_id),('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                move_line_ids = data_obj.search(cr, uid, [('move_line_id', '=', active_id),
#                                                ('distribution_id','=',wizard_value.distribution_id.id)], context=context)
#                #print"MOVE LINE IDS:",move_line_ids
#                if move_line_ids:
#                    vals ={'analytic_account_id': wizard_value.analytic_account_id.id}
#                    data_obj.write(cr, uid, move_line_ids, vals, context=context)
#                else:
#                    vals = {'distribution_id': wizard_value.distribution_id.id,
#                             'analytic_account_id': wizard_value.analytic_account_id.id,
#                             'wiz_move_id': move_line.move_id.id,
#                             'move_line_id': move_line.id
#                    }
#                    data_obj.create(cr, uid, vals, context=context)
#
#        return True
#
##    def onchange_clear_accounts(self, cr, uid, ids, wizard_link_id, context=None):
##        """clear the account lines from the wizard"""
##        res = {}
##        wiz = []
##        print "IDS:",ids
##        print "CONTEXT:",context
##        print "WLID:",wizard_link_id
##
##        data = self.pool.get('wizard.data').search(cr, uid, [('wiz_invoice_line_id','=',context['active_id'])])
##        print "DATA:",data
##
##        i=0
##        for wizard_value in wizard_link_id:
##            wiz.append([])
##            wiz[i].append(1)
##            wiz[i].append(data[i])
##            wiz[i].append({'account_analytic_id':False})
##            wiz[i].append({'account_analytic_required':False})
##            wiz[i].append({'distribution_id':wizard_value[2]['distribution_id'] or False})
##            i+=1
##        
##        res['clear_accounts'] = False
##        res['wizard_link_id'] = wiz
##        print "res:",res
##        return {'value':res}
#
#account_analytic_dimension_distribution()
#
#class account_analytic_dimension_distribution_wizard(osv.osv):
#    _name = 'account.analytic.dimension.distribution.wizard'
#
#    _columns = {
#        'name': fields.char('Name'),
#        'wizard_id': fields.many2one('account.analytic.dimension.distribution', 'Wizard ID'),
#        'move_line_id': fields.many2one('account.move.line', 'Account Move Line'),
#        'wiz_invoice_line_id': fields.many2one('account.invoice.line', 'Account Invoice Line'),
#        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
#        'sale_order_line_id': fields.many2one('sale.order.line', 'Sales Order Line'),
#        'purchase_order_id': fields.many2one('purchase.order', 'Purchase Order'),
#        'purchase_order_line_id': fields.many2one('purchase.order.line', 'Purchase OrderLine'),
#        'distribution_id': fields.many2one('account.analytic.dimension', 'Dimension', readonly=True),
#        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
#        'analytic_account_required': fields.boolean('Analytic Account Required'),
#        'statement_id': fields.many2one('account.bank.statement', 'Bank Statement'),
#        'statement_line_id': fields.many2one('account.bank.statement.line', 'Bank Statement Line'),
#        'invoice_tax_id': fields.many2one('account.invoice.tax', 'Invoice Tax Line', ondelete="cascade"),
#    }
#
#account_analytic_dimension_distribution_wizard()

class wizard_data(osv.osv):
    _name = 'wizard.data'
    
    _columns = {
        'wiz_move_id': fields.many2one('account.move', 'Account Move'),
        'move_line_id': fields.many2one('account.move.line', 'Account Move Line'),
        'wiz_invoice_id': fields.many2one('account.invoice', 'Account Invoice'),
        'wiz_invoice_line_id': fields.many2one('account.invoice.line', 'Account Invoice Line'),
        'sale_order_id': fields.many2one('sale.order', 'Sale Order'),
        'sale_order_line_id': fields.many2one('sale.order.line', 'Sale OrderLine'),
        'purchase_order_id': fields.many2one('purchase.order', 'Purchase Order'),
        'purchase_order_line_id': fields.many2one('purchase.order.line', 'Purchase OrderLine'),
        'distribution_id': fields.many2one('account.analytic.dimension', 'Dimension'),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'analytic_account_required': fields.boolean('Analytic Account Required'),
        'statement_id': fields.many2one('account.bank.statement', 'Bank Statement'),
        'statement_line_id': fields.many2one('account.bank.statement.line', 'Bank Statement Line'),
        'invoice_tax_id': fields.many2one('account.invoice.tax', 'Invoice Tax Line', ondelete="cascade"),
    }

wizard_data()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
