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
import openerp.addons.decimal_precision as dp

class account_invoice(osv.osv):

    _inherit = 'account.invoice'

    def _store_set_values(self, cr, uid, ids, fields, context=None):
        """force multi function_field 'amount_total_signed' to use the _amount_all function
        of the inherited account_invoice class
        """        
        return super(account_invoice, self)._store_set_values(
                cr, uid, ids, 
                sorted(fields, key = lambda x: 0 if x=='amount_total_signed' else 1), context)
 
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_total_signed': 0.0
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']

            sign = -1 if invoice.type in ['in_refund','out_refund'] else 1
            res[invoice.id]['amount_total_signed'] = res[invoice.id]['amount_total'] * sign
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    _columns = {
        'amount_total_signed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Totaal (+/-)',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
    }

    def write(self, cr, uid, ids, vals, context=None):
        """Do not allow to validate an invoice for an unactive partner"""
        for inv in self.browse(cr, uid, ids):
            if not inv.partner_id.active:
                raise osv.except_osv(_('Error!'), _('You cannot validate an invoice for an unactive partner.'))
    
        return super(self, account_invoice).write(cr, uid, ids, vals, context=context)

account_invoice()

class payment_order(osv.osv):

    _inherit = 'payment.order'

    def _default_mode(self, cr, uid, context=None):
        modes = self.pool.get('payment.mode').search(cr, uid, [('type','=',4)], context=context)
        mode = False
        if len(modes) == 1:
            mode= modes[0]

        return mode

    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(payment_order, self).default_get(cr, uid, fields, context=context)

        if result['payment_order_type'] == 'payment':
            result['mode'] = self._default_mode(cr, uid, context=context)

        return result


class res_partner_bank(osv.osv):

    _inherit = 'res.partner.bank'

    _defaults = {
        'state': 'iban',
        'sequence': 1,
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
