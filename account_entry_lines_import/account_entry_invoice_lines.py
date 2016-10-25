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
from datetime import datetime
import csv
import base64
from tools.translate import _

def lookahead(iterable):
    """Pass through all values from the given iterable, augmented by the
    information if there are more values to come after the current one
    (True), or if it is the last value (False).
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    last = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield last, True
        last = val
    # Report the last value.
    yield last, False

class account_move_lines_import_wizard(osv.TransientModel):

    _name = "account.move.lines.import.wizard"

    _columns = {
        'lines_file': fields.binary('Entry Lines File', required=True),
    }

    def entry_lines_import(self, cr, uid, ids, context=None):
        """Import journal items from a file"""
        obj = self.browse(cr, uid, ids)[0]

        move = self.pool.get('account.move').browse(cr, uid, context['active_id'])

        # Find the company
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id.id

        #TODO: Replace by tempfile for Windows compatibility
        fname = '/tmp/csv_temp_' + datetime.today().strftime('%Y%m%d%H%M%S') + '.csv'
        fp = open(fname,'w+')
        fp.write(base64.decodestring(obj.lines_file))
        fp.close()
        fp = open(fname,'rU')
        reader = csv.reader(fp, delimiter=";", quoting=csv.QUOTE_NONE)
        entry_vals = []

        for row in reader:
            if reader.line_num <= 1:
                continue

# 422
            if row[0] == "":
                raise osv.except_osv(_('No name found !'), _('No name could be found for the line %s'%(str(reader.line_num))))
# 422
            # Find the partner
            partner = False
            if row[2] != "":
                partners = self.pool.get('res.partner').search(cr, uid, [('id','=',int(row[2]))]) 
                if partners:
                    partner = partners[0]
                else:
                    raise osv.except_osv(_('No partner found !'), _('No partner could be found for that ID %s'%(row[2])))

            # Find the account
            account = False
            if row[3] == "":
                raise osv.except_osv(_('No account found !'), _('No account could be found for the line %s'%(row[0])))
            accounts = self.pool.get('account.account').search(cr, uid, [('code','=',row[3]),('company_id','=',company)])
            print "ACCOUNTS:",accounts
            if not accounts:
                raise osv.except_osv(_('No account found !'), _('No account could be found for that code %s'%(row[3])))
            account = accounts[0]

            # Find the dimensions
            dimension1 = False
            if row[4] != "":
                dimension1 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[4])])
                if not dimension1:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for that code %s'%(row[4])))
                dimension1 = dimension1[0]
            dimension2 = False
            if row[5] != "":
                dimension2 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[5])])
                if not dimension2:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for that code %s'%(row[5])))
                dimension2 = dimension2[0]
            dimension3 = False
            if row[6] != "":
                dimension3 = self.pool.get('account.analytic.account').search(cr, uid, [('code','=',row[6])])
                if not dimension3:
                    raise osv.except_osv(_('No analytic account found !'), _('No analytic account could be found for that code %s'%(row[6])))
                dimension3 = dimension3[0]

            # Find the asset
	    asset = False
            if row[7] != "":
                asset = self.pool.get('account.asset.asset').search(cr, uid, [('code','=',row[7])])  
		print "ASSET:",asset
                if not asset:
                    raise osv.except_osv(_('No asset found !'), _('No asset could be found for that code %s'%(row[7])))
		asset = asset[0]

            # Find the employee
            employee = False
            if row[8] != "":
                employees = self.pool.get('hr.employee').search(cr, uid, [('name','=',row[8])])  
                print "EMPLOYEES:",employees
                if not employees:
                    raise osv.except_osv(_('No employee found !'), _('No employee could be found for that code %s'%(row[8])))
                employee = employees[0]

            # Find the car plate
            plate = False
            if row[9] != "":
                plates = self.pool.get('fleet.vehicle').search(cr, uid, [('license_plate','ilike',row[9])])
                if plates:
                    if len(plates) > 1:
                        raise osv.except_osv(_('Multiple Car Plates found !'), _('Several car plates where found for that code %s'%(row[9])))
                    plate = plates[0]
                else:
                    raise osv.except_osv(_('No plate found !'), _('No car registration plate could be found for that reference %s'%(row[9])))

            # Find the due date
            duedate = False
            if row[10] != "": 
                df = row[10].split('/')
                duedate = df[2] + '-' + df[1].zfill(2) + '-' + df[0].zfill(2)


            # Set Debit and Credit
            debit = 0.0
            if row[11] != "":
                debit = float(row[11].replace(',','.'))
            credit = 0.0
            if row[12] != "":
                credit = float(row[12].replace(',','.'))

            # Find currency
            currency = False
            amount_currency = 0.0 
            if row[14] != "":
                currencies = self.pool.get('res.currency').search(cr, uid, [('name','=',row[14])])
                if not currencies:
                    raise osv.except_osv(_('No currency found !'), _('No currency could be found for that code %s'%(row[14])))
                currency = currencies[0]
           
                if currency:
                    amount_currency = float(row[13])

            # Find tax account
            tax_account = False
            tax_amount = 0.0
            if row[15] != "":
                if len(row[15]) == 1:
                    row[15] = row[15].zfill(2)
                tax_accounts = self.pool.get('account.tax.code').search(cr, uid, [('code','=',row[15]),('company_id','=',company)])
                print "TAX ACCOUNTS:",tax_accounts
                if not tax_accounts:
                    raise osv.except_osv(_('No tax account found !'), _('No tax account could be found for that code %s'%(row[15])))
                tax_account = tax_accounts[0]

                if tax_account:
                    tax_amount = float(row[16])

            vals = {
                'move_id': context['active_id'],
                'name': row[0],
                'ref': row[1],
                'partner_id': partner,
                'account_id': account,
                'analytic_dimension_1_id': dimension1,
                'analytic_dimension_2_id': dimension2,
                'analytic_dimension_3_id': dimension3,
                'employee_id': employee,
                'fleet_id': plate,
                'date_maturity': duedate,
                'debit': debit,
                'credit': credit,
                'currency_id': currency,
                'amount_currency': amount_currency,
                'tax_code_id': tax_account,
                'tax_amount': tax_amount, 
		'asset_id': asset,
            }
            entry_vals.append(vals)

        print "ENTRYVALS:",vals

        journal_id = move.journal_id.id
        """loop entry_vals and validate at last entry"""
        for line_vals, context['novalidate'] in lookahead(entry_vals):
            line_id = self.pool.get('account.move.line').create(cr, uid, line_vals, context=context)
            self.pool.get('account.move.line').natuurpunt_account_id_change(cr, uid, [line_id], line_vals['account_id'], line_vals['partner_id'], journal_id, context=context)

        return True

class account_move_line(osv.osv):

    _inherit = 'account.move.line'

    def default_get(self, cr, uid, fields, context=None):
        """Set account move line reference from account move reference by default"""
        if context is None:
            context = {}
        result = super(account_move_line, self).default_get(cr, uid, fields, context=context)
        if 'move_id' in context and context['move_id']:
            move = self.pool.get('account.move').browse(cr, uid, context['move_id'])
            result['ref'] = move.ref
        return result


    def create(self, cr, uid, vals, context=None, check=True):
        if context is None:
            context = {}
        if 'ref' in vals and not(vals['ref']) and 'move_id' in vals and vals['move_id']:
            move = self.pool.get('account.move').browse(cr, uid, vals['move_id'])
            vals['ref'] = move.ref
        res = super(account_move_line, self).create(cr, uid, vals, context=context, check=check)
        if 'invoice' in context and context['invoice']:
            ref = context['invoice'].reference or context['invoice'].number or False
            self.write(cr, uid, [res], {'ref':ref}, check=False, update_check=False, context=context)
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
