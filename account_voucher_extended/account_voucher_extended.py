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
from openerp.tools.translate import _
from openerp.tools import float_compare

class account_bank_statement(osv.osv):

    _inherit = "account.bank.statement"

    def action_vouchers_get(self, cr, uid, ids, context=None):
        """Get the vouchers from the statement lines"""
        if context is None:
            context = {}
        statement = self.browse(cr, uid, ids)[0]
        voucher_ids = []
        for line in statement.line_ids:
            if line.voucher_id:
                voucher_ids.append(line.voucher_id.id)
        if voucher_ids:
            mod_obj = self.pool.get('ir.model.data')
            model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_voucher_tree')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']

            return {'name': _('Account Vouchers'),
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.voucher',
                    'type': 'ir.actions.act_window',
                    'domain': [('id','in',voucher_ids),'|',('active','=',True),('active','=',False)],
                    'context': {'form_view_ref' : 'account_voucher_extended.view_account_voucher_ext_form', 'tree_view_ref' : 'account_voucher.view_voucher_tree'} 
            }
        return True

    def action_voucher_lines_get(self, cr, uid, ids, context=None):
        """Get the vouchers ines from the statement lines"""
        if context is None:
            context = {}
        statement = self.browse(cr, uid, ids)[0]
        voucher_line_ids = []
        for line in statement.line_ids:
            if line.voucher_id:
                for voucher_line in line.voucher_id.line_ids: 
                    voucher_line_ids.append(voucher_line.id)
        if voucher_line_ids:
            mod_obj = self.pool.get('ir.model.data')
            model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_account_voucher_line_extended_tree')], context=context)
            resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']

            return {'name': _('Account Voucher Lines'),
                    'context': context,
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.voucher.line',
                    'type': 'ir.actions.act_window',
                    'domain': [('id','in',voucher_line_ids)]
            }
        return True

    def unlink(self, cr, uid, ids, context=None):
        """Delete voucher at statement deletion"""
        for stmt in self.browse(cr, uid, ids):
            for line in stmt.line_ids:
                if line.voucher_id:
                    self.pool.get('account.voucher').unlink(cr, uid, [line.voucher_id.id])
        return super(account_bank_statement, self).unlink(cr, uid, ids, context=context)

class account_bank_statement_line(osv.osv):

    _inherit = "account.bank.statement.line"

    def create(self, cr, uid, vals, context=None):
        """Add the statmenet line value in the voucher"""
        stmt_id = super(account_bank_statement_line, self).create(cr, uid, vals=vals, context=context)
        if 'voucher_id' in vals and vals['voucher_id']:
            self.pool.get('account.voucher').write(cr, uid, [vals['voucher_id']], {'statement_line_id':stmt_id})
        return stmt_id

    def write(self, cr, uid, ids, vals, context=None):
        """Add the statmenet line value in the voucher"""
        if 'voucher_id' in vals and vals['voucher_id']:
           for stmt_id in ids:
            self.pool.get('account.voucher').write(cr, uid, [vals['voucher_id']], {'statement_line_id':stmt_id})
        return super(account_bank_statement_line, self).write(cr, uid, ids, vals=vals, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """Delete voucher at statement line deletion"""
        for line in self.browse(cr, uid, ids):
            if line.voucher_id:
                self.pool.get('account.voucher').unlink(cr, uid, [line.voucher_id.id])
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

class account_voucher(osv.osv):

    _inherit = "account.voucher" 


    def _get_amount_delta(self, cr, uid, ids, name, arg, context=None):
        if context is None: context = {}
        res = {}
        for voucher in self.browse(cr, uid, ids):
            amount_credit = 0.0
            amount_debit = 0.0
            statement_amount = 0.0
            if voucher.line_ids:
                if voucher.line_ids[0].statement_line_amount:
                    statement_amount = voucher.line_ids[0].statement_line_amount
            else:
                res[voucher.id] = voucher.amount
                continue

            for line in voucher.line_ids:
                if line.type == 'cr':
                     amount_credit += line.amount
                if line.type == 'dr':
                     amount_debit += line.amount
            res[voucher.id] = (statement_amount - amount_credit) + amount_debit
        return res

#    def _get_statement_line(self, cr, uid, ids, name, arg, context=None):
#        if context is None: context = {}
#        res = {}
#        for voucher in self.browse(cr, uid, ids):
#            statement = self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)])
#            print "STMT:",statement
#            if statement:
#                statement = statement[0]
#                res[voucher.id] = statement
#            else:
#		res[voucher.id] = False
#        print "STAT RES:",res
#        return res

    _columns = {
        'line_amount': fields.float("Line Amount"),
        'amount_delta': fields.function(_get_amount_delta, string='Amount Diff', type='float', store=False),
#        'statement_line_id': fields.function(_get_statement_line, string='Bank Statement Line', type='many2one', relation="account.bank.statement.line", store=True),
        'statement_line_id': fields.many2one('account.bank.statement.line', 'Bank Statement Line'),
    }

    def voucher_move_line_create(self, cr, uid, voucher_id, line_total, move_id, company_currency, current_currency, context=None):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).

        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        if context is None:
            context = {}
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        tot_line = line_total
        rec_lst_ids = []

        date = self.read(cr, uid, voucher_id, ['date'], context=context)['date']
        ctx = context.copy()
        ctx.update({'date': date})
        voucher = self.pool.get('account.voucher').browse(cr, uid, voucher_id, context=ctx)
        voucher_currency = voucher.journal_id.currency or voucher.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * voucher.payment_rate ,
            'voucher_special_currency': voucher.payment_rate_currency_id and voucher.payment_rate_currency_id.id or False,})
        prec = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        for line in voucher.line_ids:
            #create one move line per voucher line where amount is not 0.0
            # AND (second part of the clause) only if the original move line was not having debit = credit = 0 (which is a legal value)
            if not line.amount and not (line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit, precision_digits=prec) and not float_compare(line.move_line_id.debit, 0.0, precision_digits=prec)):
                continue
            # convert the amount set on the voucher line into the currency of the voucher's company
            # this calls res_curreny.compute() with the right context, so that it will take either the rate on the voucher if it is relevant or will use the default behaviour
            amount = self._convert_amount(cr, uid, line.untax_amount or line.amount, voucher.id, context=ctx)
            # if the amount encoded in voucher is equal to the amount unreconciled, we need to compute the
            # currency rate difference
            if line.amount == line.amount_unreconciled:
                if not line.move_line_id:
                    raise osv.except_osv(_('Wrong voucher line'),_("The invoice you are willing to pay is not valid anymore.\nStmt Ref: %s"%(line.statement_line_ref)))
                sign = voucher.type in ('payment', 'purchase') and -1 or 1
                currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
            else:
                currency_rate_difference = 0.0
            move_line = {
                'journal_id': voucher.journal_id.id,
                'period_id': voucher.period_id.id,
                'name': line.name or '/',
                'account_id': line.account_id.id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'currency_id': line.move_line_id and (company_currency <> line.move_line_id.currency_id.id and line.move_line_id.currency_id.id) or False,
                'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                'quantity': 1,
                'credit': 0.0,
                'debit': 0.0,
                'date': voucher.date
            }
            if amount < 0:
                amount = -amount
                if line.type == 'dr':
                    line.type = 'cr'
                else:
                    line.type = 'dr'

            if (line.type=='dr'):
                tot_line += amount
                move_line['debit'] = amount
            else:
                tot_line -= amount
                move_line['credit'] = amount

            if voucher.tax_id and voucher.type in ('sale', 'purchase'):
                move_line.update({
                    'account_tax_id': voucher.tax_id.id,
                })

            if move_line.get('account_tax_id', False):
                tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
                if not (tax_data.base_code_id and tax_data.tax_code_id):
                    raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))

            # compute the amount in foreign currency
            foreign_currency_diff = 0.0
            amount_currency = False
            if line.move_line_id:
                # We want to set it on the account move line as soon as the original line had a foreign currency
                if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency:
                    # we compute the amount in that foreign currency.
                    if line.move_line_id.currency_id.id == current_currency:
                        # if the voucher and the voucher line share the same currency, there is no computation to do
                        sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                        amount_currency = sign * (line.amount)
                    else:
                        # if the rate is specified on the voucher, it will be used thanks to the special keys in the context
                        # otherwise we use the rates of the system
                        amount_currency = currency_obj.compute(cr, uid, company_currency, line.move_line_id.currency_id.id, move_line['debit']-move_line['credit'], context=ctx)
                if line.amount == line.amount_unreconciled:
                    sign = voucher.type in ('payment', 'purchase') and -1 or 1
                    foreign_currency_diff = sign * line.move_line_id.amount_residual_currency + amount_currency

            move_line['amount_currency'] = amount_currency
            voucher_line = move_line_obj.create(cr, uid, move_line)
            rec_ids = [voucher_line, line.move_line_id.id]

            if not currency_obj.is_zero(cr, uid, voucher.company_id.currency_id, currency_rate_difference):
                # Change difference entry in company currency
                exch_lines = self._get_exchange_lines(cr, uid, line, move_id, currency_rate_difference, company_currency, current_currency, context=context)
                new_id = move_line_obj.create(cr, uid, exch_lines[0],context)
                move_line_obj.create(cr, uid, exch_lines[1], context)
                rec_ids.append(new_id)

            if line.move_line_id and line.move_line_id.currency_id and not currency_obj.is_zero(cr, uid, line.move_line_id.currency_id, foreign_currency_diff):
                # Change difference entry in voucher currency
                move_line_foreign_currency = {
                    'journal_id': line.voucher_id.journal_id.id,
                    'period_id': line.voucher_id.period_id.id,
                    'name': _('change')+': '+(line.name or '/'),
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': line.voucher_id.partner_id.id,
                    'currency_id': line.move_line_id.currency_id.id,
                    'amount_currency': -1 * foreign_currency_diff,
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': line.voucher_id.date,
                }
                new_id = move_line_obj.create(cr, uid, move_line_foreign_currency, context=context)
                rec_ids.append(new_id)
            if line.move_line_id.id:
                rec_lst_ids.append(rec_ids)
        return (tot_line, rec_lst_ids)


    def recompute_voucher_lines(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
        move_line_pool = self.pool.get('account.move.line')
        if 'default_line_amount' in context and context['default_line_amount']:
            line_amount = context['default_line_amount']
        else:
            line_amount = price

        if not context.get('move_line_ids', False):
            if line_amount >= 0:
                context['move_line_ids'] = move_line_pool.search(cr, uid, [('account_id.type', 'in', ['receivable','payable']), ('state','=','valid'), ('account_id.reconcile','=',True), ('reconcile_id', '=', False), ('partner_id', '=', partner_id), ('debit','>',0)], context=context)
            else:
                context['move_line_ids'] = move_line_pool.search(cr, uid, [('account_id.type', 'in', ['receivable','payable']), ('state','=','valid'), ('account_id.reconcile','=',True), ('reconcile_id', '=', False), ('partner_id', '=', partner_id), ('credit','>',0)], context=context)

        if not context.get('move_line_ids', False):
            return super(account_voucher,self).recompute_voucher_lines(cr, uid, ids, partner_id, journal_id, line_amount, currency_id, ttype, date, context)
        else:
            default = {
                 'value': {'line_dr_ids': [] ,'line_cr_ids': [] ,'pre_line': False,},
            }
            return default 

class account_voucher_line(osv.osv):

    _inherit = "account.voucher.line"

    _columns = {
        'move_line_partner_id': fields.related('move_line_id', 'partner_id', type='many2one', relation="res.partner", string="Journal Item Partner", store=True),
        'move_line_move_id': fields.related('move_line_id', 'move_id', type='many2one', relation="account.move", string="Journal Entry", store=True),
        'move_line_ref_id': fields.related('move_line_id', 'ref', type='char', string="Journal Item Reference", store=True),
        'statement_line_name': fields.related('voucher_id', 'statement_line_id', 'name', type='char', string="Stmt Name"),
        'statement_line_date': fields.related('voucher_id', 'statement_line_id', 'date', type='date', string="Stmt Date"),
        'statement_line_ref': fields.related('voucher_id', 'statement_line_id', 'ref', type='char', string="Stmt Ref"),
        'statement_line_partner': fields.related('voucher_id', 'statement_line_id', 'partner_id', type='many2one', relation="res.partner", string="Stmt Partner"),
        'statement_line_amount': fields.related('voucher_id', 'statement_line_id', 'amount', type='float', string="Stmt Amount"),
    }

    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        """Find reconcile boolean onchange problem with small amount difference"""
        print "in onchange_amount"
        print "context:",context
        print "amount:",amount
        print "amount_unrec",amount_unreconciled
        print "amount ==",(amount == amount_unreconciled)
        print "amount diff",(amount - amount_unreconciled)
        print "amount rounded",(round(amount,2) - round(amount_unreconciled,2))
        vals = {}  
        if amount:
            print "amount"
            vals['reconcile'] = (round(amount) == round(amount_unreconciled))
        return {'value': vals}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
