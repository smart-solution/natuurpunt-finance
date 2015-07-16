# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import openerp.addons.decimal_precision as dp

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar


class account_account(osv.osv):

    _inherit = "account.account"
    
    _columns = {
        'asset_mandatory': fields.boolean('Asset Mandatory'),
    }


    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = [] 
        args = args[:]
        ids = [] 
        try: 
            if name and str(name).startswith('partner:'):
                part_id = int(name.split(':')[1])
                part = self.pool.get('res.partner').browse(cr, user, part_id, context=context)
                args += [('id', 'in', (part.property_account_payable.id, part.property_account_receivable.id))]
                name = False
            if name and str(name).startswith('type:'):
                type = name.split(':')[1]
                args += [('type', '=', type)]
                name = False
        except:
            pass 

        if context.get('asset_id') and context.get('supplier_invoice_id'):
            asset = self.pool.get('account.asset.asset').browse(cr, user, context.get('asset_id'))
            asset_accounts = []
            asset_accounts.append(asset.category_id.account_asset_id.id or False)
            asset_accounts.append(asset.category_id.account_disinvestment_id.id or False)
            args += [('id','in', asset_accounts)]
        elif context.get('asset_id') and not context.get('supplier_invoice_id'):
            asset = self.pool.get('account.asset.asset').browse(cr, user, context.get('asset_id'))
            asset_accounts = []
            asset_accounts.append(asset.category_id.account_asset_id.id)
            asset_accounts.append(asset.category_id.account_disinvestment_id.id)
            asset_accounts.append(asset.category_id.account_gainloss_id and asset.category_id.account_gainloss_id.id or False)
            asset_accounts.append(asset.category_id.account_depreciation_id and asset.category_id.account_depreciation_id.id or False)
            asset_accounts.append(asset.category_id.account_expense_depreciation_id.id or False)
            args += [('id','in', asset_accounts)]

        if name:
            ids = self.search(cr, user, [('code', '=like', name+"%")]+args, limit=limit)
            if not ids: 
                ids = self.search(cr, user, [('shortcut', '=', name)]+ args, limit=limit)
            if not ids: 
                ids = self.search(cr, user, [('name', operator, name)]+ args, limit=limit)
            if not ids and len(name.split()) >= 2:
                #Separating code and name of account for searching
                operand1,operand2 = name.split(' ',1) #name can contain spaces e.g. OpenERP S.A.
                ids = self.search(cr, user, [('code', operator, operand1), ('name', operator, operand2)]+ args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)




account_account()

class account_asset_category(osv.osv):
    _inherit = 'account.asset.category'
    
    _columns = {
        'account_disinvestment_id': fields.many2one('account.account', 'Disinvestment Account'),
        'account_gainloss_id': fields.many2one('account.account', 'Gain/Loss Account'),
    }

account_asset_category()

class account_asset_asset(osv.osv):

    _inherit = 'account.asset.asset'
    
    def copy(self, cr, uid, ids, vals, context=None):
        vals['account_move_line_ids'] = False
        return super(account_asset_asset, self).copy(cr, uid, ids, vals, context=context)

    def _amount_purchase(self, cr, uid, ids, name, args, context=None):
        """Compute the purchase value based on the asset acount entries"""
        for asset in self.browse(cr, uid, ids, context):
            accounts = []
            accounts.append(asset.category_id.account_asset_id.id)
            if asset.category_id.account_disinvestment_id:
                accounts.append(asset.category_id.account_disinvestment_id.id)
            if asset.category_id.account_gainloss_id:
                accounts.append(asset.category_id.account_gainloss_id.id)
            cr.execute("""SELECT
                    l.asset_id as id, SUM(l.debit-l.credit) AS amount
                FROM
                    account_move_line l
                WHERE
                    l.asset_id IN %s and l.account_id in %s and l.state = 'valid' GROUP BY l.asset_id """, (tuple([asset.id]),tuple(accounts)))
            res=dict(cr.fetchall())
        for id in ids:
            res.setdefault(id, 0.0)
        return res 


    def _amount_residual(self, cr, uid, ids, name, args, context=None):
        """Compute the residual value only for the account expense depreciation account"""
        for asset in self.browse(cr, uid, ids, context):
            cr.execute("""SELECT
                    l.asset_id as id, SUM(l.credit-l.debit) AS amount
                FROM
                    account_move_line l
                WHERE
                    l.asset_id IN %s and l.account_id = %s GROUP BY l.asset_id """, (tuple([asset.id]),asset.category_id.account_depreciation_id.id))
            res=dict(cr.fetchall())
            purchase_value = self._amount_purchase(cr, uid, ids, name, args, context=context)
            res[asset.id] = purchase_value[asset.id] - res.get(asset.id, 0.0) - asset.salvage_value
        for id in ids:
            res.setdefault(id, 0.0)
        return res 

    def open_contracts(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.analytic.account',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': context,
            'domain': [('asset_ids','in',ids)]
        }


    _columns = {
        'fleet_id': fields.many2one('fleet.vehicle', 'Vehicle', select=True),
        'maintenance_id': fields.many2one('asset.asset', 'Maintenance', select=True),
        'serial_number': fields.char('Serial Number', len=32),
        'initial_depreciation_nbr': fields.integer('Initial number of depreciations'),
        'purchase_value': fields.function(_amount_purchase, method=True, digits_compute=dp.get_precision('Account'), string='Gross Value', required=False, readonly=True, store=False),
        'value_residual': fields.function(_amount_residual, method=True, digits_compute=dp.get_precision('Account'), string='Residual Value', readonly=True, store=False),
        'account_analytic_ids': fields.many2many('account.analytic.account', 'asset_account_analytic_rel', 'asset_id', 'account_id', 'Analytic Accounts'),
        'period_depreciation_amount': fields.float('Period depreciation amount'),
        'location_analytic_id': fields.many2one('account.analytic.account', 'Location - Analytic'),
        'location_partner_id': fields.many2one('res.partner', 'Location - Partner'),
        'purchase_date': fields.date('Date of Exploitation', required=True, readonly=True, states={'draft':[('readonly',False)]}),
    }


    def name_get(self, cr, uid, ids, context=None):
        res = []
        assets =  self.read(cr, uid, ids,['name', 'code'])
        if type(assets) != type([]):
            assets = [assets]
        for r in assets:
            res.append((r['id'], '[%s] %s' % (r['code'], r['name'])))
        return res

    def _compute_board_amount(self, cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=None):
        #by default amount = 0
        amount = 0 
        if i == undone_dotation_number:
            amount = residual_amount
        else:
            if asset.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(posted_depreciation_line_ids))
                if asset.prorata:
                    amount = (asset.purchase_value - asset.salvage_value) / asset.method_number
                    #amount = amount_to_depr / asset.method_number
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1:
                        purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                        if not asset.method_period % 12: 
                            for period in  range(asset.method_period / 12):
                                if period == 0:
                                    continue
                                next_year_date = (purchase_date + relativedelta(years=period))
                                next_year_days = calendar.isleap(next_year_date.year) and 366 or 365 
                                days += next_year_days
                                total_days += next_year_days
                        else:
                            total_days = calendar.monthrange(purchase_date.year, purchase_date.month)[1]
                            days = (total_days - purchase_date.day) + 1 
                            for period in range(asset.method_period):
                                if period == 0:
                                    continue
                                next_depreciation_date = (purchase_date + relativedelta(months=period))
                                next_month_days = calendar.monthrange(next_depreciation_date.year, next_depreciation_date.month)[1]
                                days += next_month_days
                                total_days += next_month_days
                       
                        amount = (asset.purchase_value / asset.method_number) / total_days * days
                        #amount = (amount_to_depr / asset.method_number) / total_days * days
                        #amount = (amount_to_depr / 10) / total_days * days
                    elif i == undone_dotation_number:
                        amount = (amount_to_depr / asset.method_number) / total_days * (total_days - days)
                        #amount = residual_amount
            elif asset.method == 'degressive':
                amount = residual_amount * asset.method_progress_factor
                if asset.prorata:
                    days = total_days - float(depreciation_date.strftime('%j'))
                    if i == 1:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * days
                    elif i == undone_dotation_number:
                        amount = (residual_amount * asset.method_progress_factor) / total_days * (total_days - days)
        return amount

    def _compute_board_undone_dotation_nb(self, cr, uid, asset, depreciation_date, total_days, context=None):
        undone_dotation_number = asset.method_number
        if asset.method_time == 'end':
            end_date = datetime.strptime(asset.method_end, '%Y-%m-%d')
            undone_dotation_number = 0 
            while depreciation_date <= end_date:
                depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, depreciation_date.day) + relativedelta(months=+asset.method_period))
                undone_dotation_number += 1
        if asset.prorata:
            undone_dotation_number += 1
        return undone_dotation_number


    def compute_depreciation_board(self, cr, uid, ids, context=None):
        depreciation_lin_obj = self.pool.get('account.asset.depreciation.line')
        currency_obj = self.pool.get('res.currency')
        for asset in self.browse(cr, uid, ids, context=context):
#            if asset.value_residual == 0.0:
#                continue
            # Fix depreciation lines with deleted account mives
            wrong_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_check', '=', True), ('move_id','=',False)])
            context['update_ok'] = True
            depreciation_lin_obj.write(cr, uid, wrong_depreciation_line_ids, {'move_check':False}, context=context)

            posted_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_check', '=', True)],order='depreciation_date desc')
            old_depreciation_line_ids = depreciation_lin_obj.search(cr, uid, [('asset_id', '=', asset.id), ('move_check', '=', False)])
            if old_depreciation_line_ids:
                depreciation_lin_obj.unlink(cr, uid, old_depreciation_line_ids, context=context)

            amount_to_depr = residual_amount = asset.value_residual
            if asset.prorata:
                #depreciation_date = datetime.strptime(self._get_last_depreciation_date(cr, uid, [asset.id], context)[asset.id], '%Y-%m-%d')
                depreciation_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                if (len(posted_depreciation_line_ids)>0):
                    last_depreciation_date = datetime.strptime(depreciation_lin_obj.browse(cr,uid,posted_depreciation_line_ids[0],context=context).depreciation_date, '%Y-%m-%d')
                    depreciation_date = (last_depreciation_date+relativedelta(months=+asset.method_period))
            else:
                #if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if (len(posted_depreciation_line_ids)>0):
                    last_depreciation_date = datetime.strptime(depreciation_lin_obj.browse(cr,uid,posted_depreciation_line_ids[0],context=context).depreciation_date, '%Y-%m-%d')
                    depreciation_date = (last_depreciation_date+relativedelta(months=+asset.method_period))
                else:
                    # depreciation_date = 1st January of purchase year
                    purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                    depreciation_date = datetime(purchase_date.year, 1, 1)
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366
            
            undone_dotation_number = self._compute_board_undone_dotation_nb(cr, uid, asset, depreciation_date, total_days, context=context)

            deprange = range(len(posted_depreciation_line_ids), undone_dotation_number + 1) 
        
            lastdep = False

            for x in deprange:
                if residual_amount <= 0.001:
                    continue
                if lastdep:
                    i = undone_dotation_number
                else:
                    i = x + 1
                amount = self._compute_board_amount(cr, uid, asset, i, residual_amount, amount_to_depr, undone_dotation_number, posted_depreciation_line_ids, total_days, depreciation_date, context=context)
                if asset.prorata and asset.method == 'linear' and asset.period_depreciation_amount:
                    amount = asset.period_depreciation_amount
                if i == asset.method_number + 1:
                    amount = residual_amount
                company_currency = asset.company_id.currency_id.id
                current_currency = asset.currency_id.id
                # compute amount into company currency
                amount = currency_obj.compute(cr, uid, current_currency, company_currency, amount, context=context)
                if (residual_amount - amount) < 0 and not lastdep:
                    lastdep = True
                    continue
                else:
                    residual_amount -= amount
                prev_residual = residual_amount
                vals = {
                     'amount': amount,
                     'asset_id': asset.id,
                     'sequence': i,
                     'name': str(asset.code) +'/' + str(i),
                     'remaining_value': residual_amount,
                     'depreciated_value': (asset.purchase_value - asset.salvage_value) - (residual_amount + amount),
                     'depreciation_date': depreciation_date.strftime('%Y-%m-%d'),
                }
                depreciation_lin_obj.create(cr, uid, vals, context=context)
                # Considering Depr. Period as months
                depreciation_date = (datetime(year, month, day) + relativedelta(months=+asset.method_period))
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year
        return True


    def set_to_open(self, cr, uid, ids, context=None):
        """reopen a closed asset"""
        return self.write(cr, uid, ids, {'state':'open'})

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args = []
        if context is None:
            context = {}
        ids = []
        if name:
            ids = self.search(cr, user, [('code', 'like', name)] + args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context or {})
        return self.name_get(cr, user, ids, context=context)


    def unlink(self, cr, uid, ids, context=None):
        """Check if the asset can be deleted"""
        for asset in self.browse(cr, uid, ids):

            # Only asset managers can delete a depreciation line
            mod_obj = self.pool.get('ir.model.data')
            model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_account_manager')], context=context)
            res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
            gp_users = [x.id for x in dim_group.users]

            if uid not in gp_users:
                raise osv.except_osv(_('Error'),_("You do not have the right to delete an asset. Only the Financial Manager can do it. Be aware that is can result in gaps in the asset numbering."))

        return super(account_asset_asset, self).unlink(cr, uid, ids, context=context)

account_asset_asset()


class account_asset_depreciation_line(osv.osv):

    _inherit = 'account.asset.depreciation.line'

    def create_move(self, cr, uid, ids, context=None):
        # Only asset managers can delete a depreciation line
        mod_obj = self.pool.get('ir.model.data')
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_multi_analytic_dimension_manager')], context=context)
        res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
        gp_users = [x.id for x in dim_group.users]

        if uid not in gp_users:
            raise osv.except_osv(_('Error'),_("You do not have the right to preocess an asset depreciation line"))

        can_close = False
        if context is None:
            context = {}

        context['check'] = False
        context['novalidate'] = True

        asset_obj = self.pool.get('account.asset.asset')
        period_obj = self.pool.get('account.period')
        move_obj = self.pool.get('account.move')
        move_line_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')
        created_move_ids = []
        asset_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            
            # Check if the previous asset has been depreciated
            if line.sequence > 1:
                prevline_id = self.search(cr, uid, [('asset_id','=',line.asset_id.id), ('sequence','=',line.sequence - 1)])
                if prevline_id:
                    prevline = self.browse(cr, uid, prevline_id[0])
                    if not prevline.move_id:
                        raise osv.except_osv(_('Error'),_('You cannot process a depreciation line if the previous line has not been processed\nAsset: %s (%s)'%(line.asset_id.name, line.asset_id.code)))

            depreciation_date = context.get('depreciation_date') or time.strftime('%Y-%m-%d')
            ctx = dict(context, account_period_prefer_normal=True)
            period_ids = period_obj.find(cr, uid, depreciation_date, context=ctx)
            company_currency = line.asset_id.company_id.currency_id.id
            current_currency = line.asset_id.currency_id.id
            context.update({'date': depreciation_date})
            amount = currency_obj.compute(cr, uid, current_currency, company_currency, line.amount, context=context)
            sign = (line.asset_id.category_id.journal_id.type == 'purchase' and 1) or -1
            asset_name = line.asset_id.name
            reference = line.name
            move_vals = { 
                'name': asset_name,
                'date': depreciation_date,
                'ref': reference,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': line.asset_id.category_id.journal_id.id,
                }
            move_id = move_obj.create(cr, uid, move_vals, context=context)
            journal_id = line.asset_id.category_id.journal_id.id
            partner_id = line.asset_id.partner_id.id
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_depreciation_id.id,
                'debit': 0.0,
                'credit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and  current_currency or False,
                'amount_currency': company_currency != current_currency and - sign * line.amount or 0.0,
                'date': depreciation_date,
            }, context=context)
            move_line_obj.create(cr, uid, {
                'name': asset_name,
                'ref': reference,
                'move_id': move_id,
                'account_id': line.asset_id.category_id.account_expense_depreciation_id.id,
                'credit': 0.0,
                'debit': amount,
                'period_id': period_ids and period_ids[0] or False,
                'journal_id': journal_id,
                'partner_id': partner_id,
                'currency_id': company_currency != current_currency and  current_currency or False,
                'amount_currency': company_currency != current_currency and sign * line.amount or 0.0,
                'date': depreciation_date,
                'asset_id': line.asset_id.id
           }, context=context)
            self.write(cr, uid, line.id, {'move_id': move_id}, context=context)
            created_move_ids.append(move_id)


        res = created_move_ids

        for asset_line in self.browse(cr, uid, ids):
            # Find period
            period_res = self.pool.get('account.period').find(cr, uid, asset_line.depreciation_date, context=context)
            period = period_res[0]
            if len(period_res) > 1:
                # In case of several periods for same date (ex: opening balance), take the last created one
                period = period_res[-1]
            move = self.pool.get('account.move').browse(cr, uid, asset_line.move_id.id)
            move_ref = asset_line.asset_id.code + '/' +  move.ref.split('/')[-1]
            self.pool.get('account.move').write(cr, uid, [move.id], {'ref':move_ref, 'date':asset_line.depreciation_date, 'period_id': period})

            # Set the asset_id on all move lines
            for move_line in asset_line.move_id.line_id:
                if not move_line.asset_id:
                    r = self.pool.get('account.move.line').write(cr, uid, [move_line.id], {'asset_id':asset_line.asset_id.id})

        return res


    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(account_asset_depreciation_line, self).default_get(cr, uid, fields, context=context)

        # Copy the asset value of the last created line
        if 'asset_id' in context and context['asset_id']:
            result['asset_id'] = context['asset_id']
        return result

    def write(self, cr, uid, ids, vals, context=None):
        """ Only Asset Managers can modify a depreciation line """
        if 'update_ok' not in context or ('update_ok' in context and not context['update_ok']):
            mod_obj = self.pool.get('ir.model.data')
            model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_multi_analytic_dimension_manager')], context=context)
            res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
            dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
            gp_users = [x.id for x in dim_group.users]

            if uid not in gp_users:
                raise osv.except_osv(_('Error'),_("You do not have the right to modify an asset depreciation line"))

        return super(account_asset_depreciation_line, self).write(cr, uid, ids, vals, context=context)


    def unlink(self, cr, uid, ids, context=None):
        """Check if the line can be deleted"""
        for line in self.browse(cr, uid, ids):
            if line.move_id and (line.move_id.state != 'draft' or line.move_id.name != '/'):
                raise osv.except_osv(_('Error'),_('You cannot delete a depreciation line for a confirmed journal entry'))

            # Only asset managers can delete a depreciation line
            if 'update_ok' not in context or ('update_ok' in context and not context['update_ok']):
                mod_obj = self.pool.get('ir.model.data')
                model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'res.groups'), ('name', '=', 'group_multi_analytic_dimension_manager')], context=context)
                res_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
                dim_group = self.pool.get('res.groups').browse(cr, uid, res_id)
                gp_users = [x.id for x in dim_group.users]

                if uid not in gp_users:
                    raise osv.except_osv(_('Error'),_("You do not have the right to delete an asset depreciation line"))

            if line.move_id and line.move_id.state == 'draft':
                self.pool.get('account.move').unlink(cr, uid, [line.move_id.id])

        return super(account_asset_depreciation_line, self).unlink(cr, uid, ids, context=context)

account_asset_depreciation_line()

class account_move(osv.osv):

    _inherit = 'account.move'

    def button_validate(self, cursor, user, ids, context=None):
        """Check on required asset and account"""
        for move in self.browse(cursor, user, ids):
            for line in move.line_id:
                if line.account_id.asset_mandatory and not line.asset_id and not line.move_id.journal_id.overrule_mandatory:
                    raise osv.except_osv(_('Error'),_('The account %s requires an asset'%(line.account_id.code)))
                if line.asset_id:
                    asset_accounts = []
                    asset_accounts.append(line.asset_id.category_id.account_asset_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_disinvestment_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_gainloss_id and line.asset_id.category_id.account_gainloss_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_depreciation_id and line.asset_id.category_id.account_depreciation_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_expense_depreciation_id.id or False)
                    if line.account_id.id not in asset_accounts:
                        raise osv.except_osv(_('Error'),_('This account %s does not match any of the accounts of the asset'%(line.account_id.code)))

        return super(account_move, self).button_validate(cursor, user, ids, context=context)

    def post(self, cr, uid, ids, context=None):
        """Update the gross value of the asset"""    
        result = super(account_move, self).post(cr, uid, ids, context=context)
        for move in self.browse(cr, uid, ids):
            for line in move.line_id:
                if line.asset_id:
                    if line.account_id.id == line.asset_id.category_id.account_asset_id.id or \
                            line.account_id.id == (line.asset_id.category_id.account_disinvestment_id and line.asset_id.category_id.account_disinvestment_id.id or False) or \
                            line.account_id.id == (line.asset_id.category_id.account_gainloss_id and line.asset_id.category_id.account_gainloss_id.id or False):
                        if line.debit:
                            gross_val = line.asset_id.purchase_value + line.debit
                        elif line.credit:
                            gross_val = line.asset_id.purchase_value - line.credit
                        else:
                            continue
                        self.pool.get('account.asset.asset').write(cr, uid, [line.asset_id.id], {'purchase_value':gross_val})
                        self.pool.get('account.asset.asset').compute_depreciation_board(cr, uid, [line.asset_id.id], context=context)
        return result

account_move()


class account_move_line(osv.osv):

    _inherit = 'account.move.line'

    _columns = {
        'asset_id': fields.many2one('account.asset.asset', 'Asset'),
#        'asset_mandatory': fields.related('account_id', 'asset_mandatory', type="boolean", string='Asset Mandatory', readonly=True),
        'asset_mandatory': fields.boolean('Asset Mandatory'),
    }

    def create(self, cr, uid, vals, context=None):
        """Assign the invoice line asset to the account move line if existing"""
        res = super(account_move_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, res)
        
        if line.invoice_line_id.asset_id:
            self.write(cr, uid, [res], {'asset_id':line.invoice_line_id.asset_id.id})
        return res

    
    def onchange_asset(self, cr, uid, ids, asset_id, context=None):
        res = {}
        if asset_id:
            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
            res['account_id'] = asset.category_id.account_asset_id.id
        return {'value':res}


    def onchange_account(self, cr, uid, ids, account_id, asset_id, context=None):
        res = {}
        if asset_id:
            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
            if asset.category_id.account_asset_id.id != account_id:
                raise osv.except_osv(_('Error'),_('This account does not match the asset account %s'%(asset.category_id.account_asset_id.code)))
            res['account_id'] = asset.category_id.account_asset_id.id
            res['asset_mandatory'] = False
            if asset.category_id.account_asset_id.asset_mandatory:
                res['asset_mandatory'] = True
        return {'value':res}

account_move_line()

class account_invoice_line(osv.osv):

    _inherit = 'account.invoice.line'

    _columns = {
        'asset_id': fields.many2one('account.asset.asset', 'Asset', domain="[('state', '=', 'draft')]"),
        'asset_mandatory': fields.related('account_id', 'asset_mandatory', type="boolean", string='Asset Mandatory', readonly=True),
    }

    def onchange_asset(self, cr, uid, ids, asset_id, context=None):
        res = {}
        if asset_id:
            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
            res['account_id'] = asset.category_id.account_asset_id.id
        return {'value':res}

    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(account_invoice_line, self).default_get(cr, uid, fields, context=context)

        # Copy the asset value of the last created line
        if 'id' in context and context['id']:
            lines = self.pool.get('account.invoice').read(cr, uid, context['id'], ['invoice_line'])['invoice_line']
            if lines:
                line = self.pool.get('account.invoice.line').browse(cr, uid, max(lines))
                result['asset_id'] = line.asset_id.id
        return result


account_invoice_line()

class account_invoice(osv.osv):

    _inherit = 'account.invoice'

    def action_move_create(self, cr, uid, ids, context=None):
        """Check if the asset account is a proper one"""
        for inv in self.browse(cr, uid, ids):
            for line in inv.invoice_line:
                if line.account_id.asset_mandatory and not line.asset_id:
                    raise osv.except_osv(_('Error'),_('The account %s requires an asset'%(line.account_id.code)))
                if line.asset_id:
                    asset_accounts = []
                    asset_accounts.append(line.asset_id.category_id.account_asset_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_disinvestment_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_gainloss_id and line.asset_id.category_id.account_gainloss_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_depreciation_id and line.asset_id.category_id.account_depreciation_id.id or False)
                    asset_accounts.append(line.asset_id.category_id.account_expense_depreciation_id.id or False)
                    if line.account_id.id not in asset_accounts:
                        raise osv.except_osv(_('Error'),_('The account %s does not match any of the accounts of the asset'%(line.account_id.code)))
                if line.asset_id and line.asset_id.state != 'draft':
                    raise osv.except_osv(_('Error'),_('The asset %s should be in draft state in order to validate that invoice'%(line.asset_id.name)))

        return super(account_invoice, self).action_move_create(cr, uid, ids, context=context)

account_invoice()

#class account_bank_statement(osv.osv):
#
#    _inherit = 'account.bank.statement'
#
#    def button_confirm_bank(self, cr, uid, ids, context=None):
#        """Do checks for Assets"""
#        for statement in self.browse(cr, uid, ids):
#            for line in statement.line_ids:
#                if line.account_id.asset_mandatory and not line.asset_id:
#                    raise osv.except_osv(_('Error'),_('This account (%s) requires an asset'%(line.account_id.code)))
#                if line.asset_id:
#                    asset_accounts = []
#                    asset_accounts.append(line.asset_id.category_id.account_asset_id.id or False)
#                    asset_accounts.append(line.asset_id.category_id.account_disinvestment_id.id or False)
#                    asset_accounts.append(line.asset_id.category_id.account_gainloss_id and line.asset_id.category_id.account_gainloss_id.id or False)
#                    asset_accounts.append(line.asset_id.category_id.account_depreciation_id and line.asset_id.category_id.account_depreciation_id.id or False)
#                    asset_accounts.append(line.asset_id.category_id.account_expense_depreciation_id.id or False)
#                    if line.account_id.id not in asset_accounts:
#                        raise osv.except_osv(_('Error'),_('This account %s does not match any of the accounts of the asset'%(line.account_id.code)))
#        return super(account_bank_statement, self).button_confirm_bank(cr, uid, ids, context=context)
#
#
#account_bank_statement()

class account_bank_statement_line(osv.osv):

    _inherit = 'account.bank.statement.line'

    _columns = {
        'asset_id': fields.many2one('account.asset.asset', 'Asset'),
        'asset_mandatory': fields.related('account_id', 'asset_mandatory', type="boolean", string='Asset Mandatory', readonly=True),
    }

#    def onchange_asset(self, cr, uid, ids, asset_id, context=None):
#        res = {}
#        if asset_id:
#            asset = self.pool.get('account.asset.asset').browse(cr, uid, asset_id)
#            res['account_id'] = asset.category_id.account_asset_id.id
#        return {'value':res}
#
#account_bank_statement_line()


class account_analytic_account(osv.osv):

    _inherit = 'account.analytic.account'

    _columns = {
            'asset_ids': fields.many2many('account.asset.asset', 'account_analytic_asset_rel', 'asset_id', 'account_id', 'Asset'),
    }
account_analytic_account()

class asset_modify(osv.osv_memory):

    _inherit = 'asset.modify'

    def modify(self, cr, uid, ids, context=None):
        asset = self.pool.get('account.asset.asset').browse(cr, uid, context['active_id'], context=context)
        if asset.state in ('open','close'):
            raise osv.except_osv(_('Error'),_('You cannot change the duration of a running or closed asset'))
            


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
