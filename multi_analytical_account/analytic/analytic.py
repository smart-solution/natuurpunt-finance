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
import openerp.addons.decimal_precision as dp

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'

    def _np_debit_credit_bal_qtty(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        if context is None:
            context = {}
        if ids and not(self.read(cr, uid, ids, ['active'])[0]['active']):
            child_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)],context={'active_test': False,}))
        else:
            child_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)]))
        for i in child_ids:
            res[i] =  {}
            for n in fields:
                res[i][n] = 0.0

        if not child_ids:
            return res

        where_date = ''
        where_clause_args = [tuple(child_ids)]
        if context.get('from_date', False):
            where_date += " AND l.date >= %s"
            where_clause_args  += [context['from_date']]
        if context.get('to_date', False):
            where_date += " AND l.date <= %s"
            where_clause_args += [context['to_date']]
        cr.execute("""
              SELECT a.id,
                     sum(
                         CASE WHEN l.amount > 0
                         THEN l.amount
                         ELSE 0.0
                         END
                          ) as debit,
                     sum(
                         CASE WHEN l.amount < 0
                         THEN -l.amount
                         ELSE 0.0
                         END
                          ) as credit,
                     COALESCE(SUM(l.amount),0) AS balance,
                     COALESCE(SUM(l.unit_amount),0) AS quantity
              FROM account_analytic_account a
                  LEFT JOIN account_analytic_line l ON (a.id = l.account_id)
              WHERE a.id IN %s
              """ + where_date + """
              GROUP BY a.id""", where_clause_args)
        for row in cr.dictfetchall():
            res[row['id']] = {}
            for field in fields:
                res[row['id']][field] = row[field]
        return self._compute_level_tree(cr, uid, ids, child_ids, res, fields, context)

    _columns = {
        'dimension_id': fields.many2one('account.analytic.dimension', 'Analytical Dimension'),
        'allowed_account_ids': fields.many2many('account.analytic.account', 'account_analytic_account_allowed_rel', 'account_id', 'allowed_account_id', 'Allowed Analytic Accounts'),
        'dimensions_mandatory': fields.boolean('Dependent Dimensions Mandatory'),
        'active': fields.boolean('Active'),
        'default_dimension_1_id': fields.many2one('account.analytic.account', 'Default Analytic Account for Dimension 1'),
        'default_dimension_2_id': fields.many2one('account.analytic.account', 'Default Analytic Account for Dimension 2'),
        'default_dimension_3_id': fields.many2one('account.analytic.account', 'Default Analytic Account for Dimension 3'),
        'dimension_sequence': fields.related('dimension_id', 'sequence', type="integer", string="Dimension Sequence", store=True),
        'old_code': fields.char('Old Code', size=64),
        'balance': fields.function(_np_debit_credit_bal_qtty, type='float',
                                   string='Balance',
                                   multi='debit_credit_bal_qtty',
                                   digits_compute=dp.get_precision('Account')),
        'debit': fields.function(_np_debit_credit_bal_qtty, type='float',
                                 string='Debit',
                                 multi='debit_credit_bal_qtty',
                                 digits_compute=dp.get_precision('Account')),
        'credit': fields.function(_np_debit_credit_bal_qtty, type='float',
                                  string='Credit',
                                  multi='debit_credit_bal_qtty',
                                  digits_compute=dp.get_precision('Account')),
        'quantity': fields.function(_np_debit_credit_bal_qtty,
                                    type='float', string='Quantity',
                                    multi='debit_credit_bal_qtty'),
    }

    _order = 'code'

    _defaults = {
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not len(ids):
            return []

        res = []
        for account in self.browse(cr, uid, ids, context=context):
            #print "ACC:",account
            if account.code:
                name = '[%s] %s'%(account.code,account.name)
            else:
                name = account.name
            res.append((account.id,name))
        return res


    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=100):
        print "ANA name_search context:",context
        user  = self.pool.get('res.users').browse(cr, uid, uid)
        ids = []
        if not args:
            args = []
        if context is None:
            context = {}
        if context.get('distribution_id'):
            args += [('dimension_id', '=', context['distribution_id'])]

        if context.get('wizard_link_id'):
            # Search for the allowed multi-analytical accounts
            for line in context.get('wizard_link_id'):
                if 'analytic_account_id' in line[2] and line[2]['analytic_account_id']:
                    allowed_accounts = self.read(cr, uid, line[2]['analytic_account_id'], ['allowed_account_ids'])
                    print "Allowed accounts:",allowed_accounts
                    args += [('id','in',allowed_accounts['allowed_account_ids'])]

        if context.get('dimension'):
	    allowed_dimensions = []
	    if 'purchase_line_id' in context or 'sale_line_id' in context or 'purchase_requisition_line_id' in context:
		    # Set all dimensions allowed
		    allowed_dimensions = self.pool.get('account.analytic.dimension').search(cr, uid, [], context=context)
		    print "Allowed DIMS:",allowed_dimensions
	    elif 'analytic_account_id' in context:
		    # Set all dimensions allowed
		    allowed_dimensions = self.pool.get('account.analytic.dimension').search(cr, uid, [], context=context)
		    print "Allowed DIMS:",allowed_dimensions
		    allowed_accounts = self.read(cr, uid, context['analytic_account_id'], ['allowed_account_ids'])['allowed_account_ids']
                    args += [('id','in',allowed_accounts)]
	    else:
		    # Check for allowed dimension in financial documents
		    account_dimensions = self.pool.get('account.account').read(cr, uid, context.get('account_id'), ['dimension_ids'])['dimension_ids']
		    for accdim in self.pool.get('account.account.analytic.dimension').browse(cr, uid, account_dimensions):
			allowed_dimensions.append(accdim.dimension_id.id)
		    print "Allowed DIMS:",allowed_dimensions
		    print "DIMENSION:",context['dimension']

            if context['dimension'] == 1:
                dimension_ids = self.pool.get('account.analytic.dimension').search(cr, uid, [('sequence','=',1),('company_id','=',user.company_id.id)])
                print "DIMS IDS:",dimension_ids
                if dimension_ids and (dimension_ids[0] in allowed_dimensions):
                    args += [('dimension_id','in',dimension_ids)]

                    if 'dimension2' in context and context['dimension2']:
                        allowed_accounts2 = self.read(cr, uid, context['dimension2'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts2)]
                    if 'dimension3' in context and context['dimension3']:
                        allowed_accounts3 = self.read(cr, uid, context['dimension3'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts3)]
                else:
                    return False

            if context['dimension'] == 2:
                dimension_ids = self.pool.get('account.analytic.dimension').search(cr, uid, [('sequence','=',2),('company_id','=',user.company_id.id)])
                if dimension_ids and (dimension_ids[0] in allowed_dimensions):
                    args += [('dimension_id','in',dimension_ids)]
                    
                    if 'dimension1' in context and context['dimension1']:
                        allowed_accounts1 = self.read(cr, uid, context['dimension1'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts1)]
                    if 'dimension3' in context and context['dimension3']:
                        allowed_accounts3 = self.read(cr, uid, context['dimension3'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts3)]
                else:
                    return False

            if context['dimension'] == 3:
                dimension_ids = self.pool.get('account.analytic.dimension').search(cr, uid, [('sequence','=',3),('company_id','=',user.company_id.id)])
                if dimension_ids and (dimension_ids[0] in allowed_dimensions):
                    args += [('dimension_id','in',dimension_ids)]

                    if 'dimension1' in context and context['dimension1']:
                        allowed_accounts1 = self.read(cr, uid, context['dimension1'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts1)]
                    if 'dimension2' in context and context['dimension2']:
                        allowed_accounts2 = self.read(cr, uid, context['dimension2'], ['allowed_account_ids'])['allowed_account_ids']
                        args += [('id','in',allowed_accounts2)]
                else:
                    return False

        if name:
            ids = self.search(cr, uid, [('code', 'ilike', name)] + args, limit=limit, context=context)
            if not ids:
                domain = []
                for name2 in name.split('/'):
                    name = name2.strip()
                    ids = self.search(cr, uid, domain + [('name', 'ilike', name)] + args, limit=limit, context=context)
                    if not ids: break
                    domain = [('parent_id','in',ids)]
        else:
            print "ARGS;",args
            ids = self.search(cr, uid, args, context=context, limit=limit)

        print "IDS:",ids
        return self.name_get(cr, uid, ids, context)

    def create(self, cr, uid, vals, context=None):
        """Doesn't allow 2 acccounts with same code for the same company"""
        print 'VALS:',vals
        if 'code' in vals and vals['code']:
            acc_ids = self.search(cr, uid, [('code','=',vals['code']),('company_id','=',vals['company_id']),'|',('active','=',True),('active','=',False)])
            print "ACCIDS:",acc_ids
            if acc_ids:
                raise osv.except_osv(_('Error!'), _('An analytic account already exist for that reference in the same company'))

        """Create the analytical account in the allowed account"""
        res =  super(account_analytic_account, self).create(cr, uid, vals, context=context)
        if 'allowed_account_ids' in vals and vals['allowed_account_ids'] and vals['allowed_account_ids'][0][2] :
            context['no_loop_write'] = True        
            self.write(cr, uid, vals['allowed_account_ids'][0][2], {'allowed_account_ids':[(4,res)]}, context=context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """Create the analytical account in the allowed account"""
        for account in self.browse(cr, uid ,ids):
            """Doesn't allow 2 acccounts with same code for the same company"""
            if 'code' in vals and vals['code']:
                acc_ids = self.search(cr, uid, [('code','=',vals['code']),('company_id','=',account.company_id.id),'|',('active','=',True),('active','=',False)])
                if acc_ids:
                    raise osv.except_osv(_('Error!'), _('An analytic account already exist for that reference in the same company'))
            if 'allowed_account_ids' in vals and vals['allowed_account_ids'] and 'no_loop_write' not in context:
                new_accounts = vals['allowed_account_ids'][0][2]
                old_accounts = []
                for acc in account.allowed_account_ids:
                    old_accounts.append(acc.id)

                if len(new_accounts) > len(old_accounts):
                    # If accounts are added
                    added_accounts = list(set(new_accounts) - set(old_accounts))
                    context['no_loop_write'] = True        
                    self.write(cr, uid, added_accounts, {'allowed_account_ids':[(4,account.id)]}, context=context)
                   #print "ADDED %s to %s:"%(account.id,added_accounts)
                elif len(new_accounts) < len(old_accounts):
                    # If accounts are removed
                    removed_accounts = list(set(old_accounts) - set(new_accounts))
                    context['no_loop_write'] = True        
                    self.write(cr, uid, removed_accounts, {'allowed_account_ids':[(3,account.id)]}, context=context)
                   #print "REMOVED:",removed_accounts
                elif set(new_accounts) != set(old_accounts):
                    # if account are replaced
                    replaced_new_accounts = list(set(new_accounts) - set(old_accounts))
                    replaced_old_accounts = list(set(old_accounts) - set(new_accounts))
                    context['no_loop_write'] = True        
                   #print "REPLACED:%s by %s"%(replaced_old_accounts, replaced_new_accounts)
                    self.write(cr, uid, replaced_new_accounts, {'allowed_account_ids':[(4,account.id)]}, context=context)
                    self.write(cr, uid, replaced_old_accounts, {'allowed_account_ids':[(3,account.id)]}, context=context)

        return super(account_analytic_account, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        analytic = self.browse(cr, uid, id, context=context)
        default.update(
            child_ids = False,
            code = False,
            line_ids = False,
            name = _("%s (copy)") % (analytic['name']))
        res =  super(account_analytic_account, self).copy(cr, uid, id, default, context=context)

        # Insure that the allowed dimentions are correct
        context['no_loop_write'] = True
        for allowacc in analytic.allowed_account_ids:
            self.write(cr, uid, [allowacc.id], {'allowed_account_ids':[(4,res)]}, context=context)

        return res

account_analytic_account()

class account_analytic_line(osv.osv):

    _inherit = 'account.analytic.line'

    _columns = {
            'period_id': fields.many2one('account.period', 'Accounting Period'),
            'journal_entry_id': fields.related('move_id', 'move_id', type='many2one', relation='account.move', string='Journal Entry'),
           'dimension_id': fields.related('account_id', 'dimension_id', type='many2one', relation='account.analytic.dimension', string='Dimension', store=True),
    }

    def unlink(self, cr, uid, ids, context=None):
        print "analytic line unlink"
        print "unlink context:",context
#        if uid != 1 and 'from_view' in context:
#            raise osv.except_osv(_('Error!'), _('Only the admin user can delete analytic lines'))
        return super(account_analytic_line, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        res = super(account_analytic_line, self).create(cr, uid, vals=vals, context=context)

        line = self.browse(cr, uid, res)

        if line.move_id and line.move_id.currency_id and line.move_id.currency_id.name != 'EUR':
            print "line debit:",line.move_id.debit
            print "line credit:",line.move_id.credit
            if line.move_id.debit != 0.0:
                amount = -line.move_id.debit
            elif line.move_id.credit != 0.0:
                amount = line.move_id.credit
            else:
                amount = 0.0
            self.write(cr, uid, [res], {'amount':amount})

        return res

account_analytic_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
