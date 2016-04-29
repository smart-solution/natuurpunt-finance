# -*- coding: utf-8 -*-
##############################################################################
#
#    Smart Solution bvba
#    Copyright (C) 2010-Today Smart Solution BVBA (<http://www.smartsolution.be>).
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
 
from osv import osv, fields
from tools.translate import _
import time

class res_partner(osv.osv):
"""comm"""
    _inherit = 'res.partner'

#    _sql_constraints = [
#        ('vat_uniq', 'unique(vat)', 'Error! The VAT number already exists!'),
#    ]

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        res = []
        for partner in self.browse(cr, uid, ids, context=context):
            name = '[%s] %s'%(str(partner.id), partner.name)
            res.append((partner.id,name))
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
            if name.isdigit():
                ids = self.search(cr, user, [('id', '=', int(name))] + args, limit=limit, context=context)
            else:
                ids = self.search(cr, user, [('name', 'ilike', name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context or {})
        return self.name_get(cr, user, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        """Add the np sequence reference"""
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('code','=','res.partner.np.ref')])
        vals['ref'] = self.pool.get('ir.sequence').next_by_id(cr, uid, seq_id, context)
        return super(res_partner, self).create(cr, uid, vals, context=context)

    _defaults = {
        'company_id': False,
    }

res_partner()

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def _payment_sent_check(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for inv in self.browse(cr, uid ,ids):
            result[inv.id] = False
            payments = self.pool.get('payment.line').search(cr, uid, [('move_line_id.move_id.id','=',inv.move_id.id)])                              
            for payment in self.pool.get('payment.line').browse(cr, uid, payments):        
                if payment.order_id.state == 'open' or payment.order_id.state == 'done':
                    result[inv.id] = True
                    break
        return result

    _columns = {
        'payment_sent': fields.function(_payment_sent_check, type="boolean", string="Payment Sent", store=False, readonly=True),
    }

    defaults = {
        'payment_sent': False,
    }

    def onchange_company_id(self, cr, uid, ids, company_id, part_id, type, invoice_line, currency_id):
        res = super(account_invoice, self).onchange_company_id(cr, uid, ids, company_id, part_id, type, invoice_line, currency_id)
        res['value']['journal_id'] = False
        if type == 'in_invoice' or type == 'in_refund':
            res['value']['period_id'] = False
            res['value']['date_invoice'] = False
        return res

    _sql_constraints = [
            ('supplier_number_uniq', 'unique(supplier_invoice_number, partner_id, company_id, type)', 'Error! The supplier invoice reference number already exists for this supplier within this company!'),
    ]

    def create(self, cr, uid, vals, context=None):
        print "VALS:",vals
        """ Fill the note with supplier invoice number"""
        if 'supplier_invoice_number' in vals and vals['supplier_invoice_number'] and ('reference' not in vals or not vals['reference']):
            vals['reference'] = vals['supplier_invoice_number']
        if 'name' in vals and vals['name']:
            vals['name'] = vals['name'].replace('/', ' /')
            print "NAME:",vals['name']
        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """ Fill the note with supplier invoice number"""
        if 'name' in vals and vals['name']:
            vals['name'] = vals['name'].replace('/', ' /')
            print "NAME:",vals['name']
        res = super(account_invoice, self).write(cr, uid, ids, vals, context=context)
        if 'supplier_invoice_number' in vals and vals['supplier_invoice_number']:
            # Slight improvement: only write once instead of per invoice
            to_write_ids = []
            for inv in self.browse(cr, uid, ids):
                if vals['supplier_invoice_number'] and (not inv.reference or inv.reference == ""):
                    to_write_ids.append(inv.id)
            if to_write_ids:
                self.write(cr, uid, to_write_ids, {'reference':vals['supplier_invoice_number']})
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """Clear the supplier reference at copy"""
        default['supplier_invoice_number'] = False
        default['reference'] = False
        return super(account_invoice, self).copy(cr, uid, id, default=default, context=context)

    def onchange_date_invoice(self, cr, uid, ids, invoice_date, payment_term, context=None):
        """Recompute due date when invoice date is modified"""
        print "IDS:",ids
        result = {'value':{}}
        if invoice_date and payment_term:
            result = self.onchange_payment_term_date_invoice(cr, uid, ids, payment_term, invoice_date)
        print "oc RES:",result
        return result

    def onchange_payment_term(self, cr, uid, ids, invoice_date, payment_term, context=None):
        """Recompute due date when payment terms are modified"""
        print "IDS:",ids
        result = {'value':{}}
        if invoice_date and payment_term:
            result = self.onchange_payment_term_date_invoice(cr, uid, ids, payment_term, invoice_date)
        print "oc RES:",result
        return result

    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        account_move_obj = self.pool.get('account.move')
        invoices = self.read(cr, uid, ids, ['move_id', 'payment_ids'])
        move_ids = [] # ones that we will need to remove
        for i in invoices:
            if i['move_id']:
                move_ids.append(i['move_id'][0])
            if i['payment_ids']:
                account_move_line_obj = self.pool.get('account.move.line')
                pay_ids = account_move_line_obj.browse(cr, uid, i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error!'), _('You cannot cancel an invoice which is partially paid. You need to unreconcile related payment entries first.'))

        # First, set the invoices as cancelled and detach the move ids
        self.write(cr, uid, ids, {'state':'cancel', 'move_id':False})
        if move_ids:
            # second, invalidate the move(s)
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            # delete the move this invoice was pointing to
            # Note that the corresponding move_lines and move_reconciles
            # will be automatically deleted too
        
            # Set a flag to bypass deletion control
            context.update({'allow_delete': True})
            account_move_obj.unlink(cr, uid, move_ids, context=context)
        self._log_event(cr, uid, ids, -1.0, 'Cancel Invoice')
        return True

    def action_date_get(self, cr, uid, ids, *args):
        retval = {}
        for inv in self.browse(cr, uid, ids):
            if not inv.date_due:
                res = self.onchange_payment_term_date_invoice(cr, uid, inv.id, inv.payment_term.id, inv.date_invoice)
                if res and res['value']:
                    retval[inv.id] = res['value']
        return retval

    def action_date_assign(self, cr, uid, ids, *args):
        val = self.action_date_get(cr, uid, ids, *args)
        if val:
            for inv_id, value in val.iteritems:
                self.write(cr, uid, [inv_id], value)
        return True

    def payment_list_get(self, cr, uid, ids, context=None):
        """Retrun the invoice payment lines"""
        inv = self.browse(cr, uid, ids)[0]
        if inv.move_id:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Payment Lines',
                    'view_mode': 'tree,form',
                    'view_type': 'form',
                    #'res_id': project_id,
                    'res_model': 'payment.line',
                    'context': context,
                    'domain': [('move_line_id.move_id.id', '=', inv.move_id.id)],
                }
        return False

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None, context=None):
        invoice_data = super(account_invoice, self)._prepare_refund(cr, uid, invoice, date=date, period_id=period_id, description=description, journal_id=journal_id, context=context)
        invoice_data['supplier_invoice_number'] = invoice.supplier_invoice_number or "/"
        return invoice_data

account_invoice()

class account_invoice_line(osv.osv):

    _inherit = "account.invoice.line"

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'fleet_id': fields.many2one('fleet.vehicle', 'Number Plate'),
        'partner_mandatory': fields.related('account_id','partner_mandatory', type="boolean", string='Partner Mandatory', readonly=True),
        'employee_mandatory': fields.related('account_id','employee_mandatory', type="boolean", string='Employee Mandatory', readonly=True),
        'fleet_mandatory': fields.related('account_id','fleet_mandatory', type="boolean", string='Number Plate Mandatory', readonly=True),
    }

account_invoice_line()


class account_account(osv.osv):
    _inherit = 'account.account'

    _columns = {
        'partner_mandatory': fields.boolean('Partner Mandatory'),
        'employee_mandatory': fields.boolean('Employee Mandatory'),
        'fleet_mandatory': fields.boolean('Number Plate Mandatory'),
        'account_group_1': fields.char('Account Group 1', size=128),
        'account_group_2': fields.char('Account Group 2', size=128),
        'account_group_3': fields.char('Account Group 3', size=128),
        'parent_consol_ids': fields.many2many('account.account', 'account_account_consol_rel', 'parent_id', 'child_id', 'Consolidated Parents'),
    }

account_account()

class account_move(osv.osv):

    _inherit = "account.move"

    _columns = {
        'journal_type': fields.related('journal_id','type', type="char", string='Journal Type', readonly=True),
        'modified': fields.boolean('Modified'),
    }

    def open_history(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        object_id = self.pool.get('ir.model').search(cr, uid, [('model','=','account.move.line')])
        res_ids = self.pool.get('account.move.line').search(cr, uid, [('move_id','=',ids[0])])
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'audittrail.log',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [('object_id','in',object_id),('res_id','in',res_ids)]
        }

    def copy(self, cr, uid, id, default=None, context=None):
        """Set date and period"""
        date = time.strftime('%Y-%m-%d')
        if default is None:
            default = {}
        default['date'] = date

        period = self.pool.get('account.period').find(cr, uid, date, context=context)
        default['period_id'] = period[0]
        return super(account_move, self).copy(cr, uid, id, default=default, context=context)

account_move()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'employee_id': fields.many2one('hr.employee', 'Employee'),
        'fleet_id': fields.many2one('fleet.vehicle', 'Number Plate'),
        'partner_mandatory': fields.related('account_id','partner_mandatory', type="boolean", string='Partner Mandatory', readonly=True),
        'employee_mandatory': fields.boolean('Employee Mandatory'),
        'fleet_mandatory': fields.boolean('Number Plate Mandatory'),
        'overrule_mandatory': fields.related('move_id', 'journal_id', 'overrule_mandatory', type='boolean', string='Disregard mandatory fields'),
    }

    def create(self, cr, uid, vals, context=None):
        """Assign the employee and plate number to the account move line if existing"""

        if context is None:
            context = {}

        if 'no_create' in context and context['no_create']:
            raise osv.except_osv(_('Warning!'), _('You cannot create journal entries from this view.'))

        res = super(account_move_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, res)

        if line.invoice_line_id:
            if line.invoice_line_id.employee_id:
                print "empl:",line.invoice_line_id.employee_id.id
                self.write(cr, uid, [res], {'employee_id':line.invoice_line_id.employee_id.id})
            if line.invoice_line_id.fleet_id:
                print "fleet:", line.invoice_line_id.fleet_id.id
                self.write(cr, uid, [res], {'fleet_id':line.invoice_line_id.fleet_id.id})

        if line.statement_line_id:
            if line.statement_line_id.employee_id:
                self.write(cr, uid, [res], {'employee_id':line.statement_line_id.employee_id.id})

        return res 


    def natuurpunt_account_id_change(self, cr, uid, ids, account_id, partner_id, journal_id, context):
        if not account_id:
            return {}
        res =  super(account_move_line, self).onchange_account_id(cr, uid, ids, account_id, partner_id, context=context)
        account_obj = self.pool.get('account.account')
        account_info = account_obj.browse(cr, uid, account_id)

        res['value']['partner_mandatory'] = False
        res['value']['employee_mandatory'] = False
        res['value']['fleet_mandatory'] = False
        res['value']['partner_mandatory'] = False

        if account_info:
            res['value']['partner_mandatory'] = account_info.partner_mandatory
            res['value']['employee_mandatory'] = account_info.employee_mandatory
            res['value']['fleet_mandatory'] = account_info.fleet_mandatory
            res['value']['partner_mandatory'] = account_info.partner_mandatory

        return res

    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        move_rec_obj = self.pool.get('account.move.reconcile')
        merges = [] 
        unmerge = [] 
        total = 0.0
        merges_rec = [] 
        company_list = [] 
        if context is None:
            context = {} 
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning!'), _('To reconcile the entries company should be the same for all entries.'))
            company_list.append(line.company_id.id)

        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id.currency_id:
                currency_id = line.account_id.currency_id
            else:
                currency_id = line.company_id.currency_id
            if line.reconcile_id:
                if line.statement_line_id:
                    raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s), Move '%s' is already reconciled!\nStmt Ref: %s\nReconciliation Code: %s") % (line.name, line.id, line.move_id.name, line.statement_line_id.ref, line.reconcile_id.name)) 
                raise osv.except_osv(_('Warning'), _("Journal Item '%s' (id: %s), Move '%s' is already reconciled!\nReconciliation Code: %s") % (line.name, line.id, line.move_id.name, line.reconcile_id.name)) 
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
                        if line2.id not in merges:
                            merges.append(line2.id)
                        if line2.account_id.currency_id:
                            total += line2.amount_currency
                        else:
                            total += (line2.debit or 0.0) - (line2.credit or 0.0) 
                merges_rec.append(line.reconcile_partial_id.id)
            else:
                unmerge.append(line.id)
                if line.account_id.currency_id:
                    total += line.amount_currency
                else:
                    total += (line.debit or 0.0) - (line.credit or 0.0) 
        if self.pool.get('res.currency').is_zero(cr, uid, currency_id, total):
            res = self.reconcile(cr, uid, merges+unmerge, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        }, context=context)
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=context)
        return True 


account_move_line()


class account_invoice_refund(osv.osv_memory):
    _inherit = "account.invoice.refund"

    def _get_journal(self, cr, uid, context=None):
        return False

    _defaults = {
        'journal_id': False,
    }

account_invoice_refund()

class account_bank_statement_line(osv.osv):

    _inherit = "account.bank.statement.line"

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee'),
#        'fleet_id': fields.many2one('fleet.vehicle', 'Number Plate'),
        'partner_mandatory': fields.related('account_id','partner_mandatory', type="boolean", string='Partner Mandatory', readonly=True),
        'employee_mandatory': fields.related('account_id','employee_mandatory', type="boolean", string='Employee Mandatory', readonly=True),
#        'fleet_mandatory': fields.related('account_id','fleet_mandatory', type="boolean", string='Number Plate Mandatory', readonly=True),
        'state': fields.related('statement_id', 'state', type='selection', selection=[('draft','New'),('confirm','Closed')], string="State", readonly=True, store=True),
    }

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        print "In onchange_employee"
        result = {'value':{}}
        if employee_id:
            employee = self.pool.get('hr.employee').browse(cr, uid, employee_id)
            if employee.analytic_account_id:
                result['value']['analytic_dimension_1_id'] = employee.analytic_account_id.id
        return result

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if 'block_statement_line_delete' in context:
                for line in self.browse(cr, uid, ids):
                    if line.statement_id.state != 'draft':
                         raise osv.except_osv(_('Error!'), _('You cannot modify a statement line for a validated statement.'))
        return super(account_bank_statement_line, self).write(cr, uid, ids, vals, context=context)

account_bank_statement_line()


class account_tax(osv.osv):

    _inherit = "account.tax"

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
            ids = self.search(cr, user, [('description', 'ilike', name)] + args, limit=limit, context=context)
            if not ids: 
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context or {})
        return self.name_get(cr, user, ids, context=context)


account_tax()

class payment_line(osv.osv):

    _inherit = "payment.line"

    _columns = {
      'payment_state':  fields.related('order_id', 'state', type='char', string="State", store=True, readonly=True),
    }

class product_product(osv.osv):


    _inherit = "product.product"

    def create(self, cr, uid, vals, context=None):
        """Add the np sequence referece"""
        seq_id = self.pool.get('ir.sequence').search(cr, uid, [('code','=','res.product.np.ref')])
        print seq_id
        vals['default_code'] = self.pool.get('ir.sequence').next_by_id(cr, uid, seq_id, context)
        print vals
        vals['company_id'] = False
        return super(product_product, self).create(cr, uid, vals, context=context)


class account_journal(osv.osv):

    _inherit = "account.journal"

    _columns = {
        'overrule_mandatory': fields.boolean('Disregard mandatory fields'),
    }

class res_company(osv.osv):

    _inherit = "res.company"

    _columns = {
        'invoice_legal_text': fields.text('Invoice Legal Notice'),
    }

class payment_order(osv.osv):

    _inherit = "payment.order"


    def _get_date_exec(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for order in self.browse(cr, uid ,ids):
            for line in order.line_ids:
                result[order.id] = line.date
                break
        return result

    _columns = {
        'execution_date': fields.function(_get_date_exec, type="date", string="Value Date", store=True),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
