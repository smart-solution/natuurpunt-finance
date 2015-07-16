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

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    def create(self, cr, uid, vals, context=None):
        """Compute the taxes when the invoice is created"""
        res = super(account_invoice, self).create(cr, uid, vals, context=context)
        if 'calc_taxes_done' not in ['context']:
#            invoice = self.browse(cr, uid, [res][0])
#            if not invoice.manual_tax:
            self.button_reset_taxes(cr, uid, [res], context)
        return res

    def write(self, cr, uid, ids, vals, context=None):
        """Compute the taxes when the invoice is saved"""
        res = super(account_invoice, self).write(cr, uid, ids, vals, context=context)
        if 'calc_taxes_done' not in ['context']:
#            invoice = self.browse(cr, uid, ids[0])
#            if not invoice.manual_tax:
            self.button_reset_taxes(cr, uid, ids, context)
        return res

    def button_reset_taxes(self, cr, uid, ids, context):
        """To avoid recursive loop"""
        if context:
            if 'calc_taxes_done' in context:
                return False
#        if context:
#            if 'manual_tax' in context and context['manual_tax']:
#                return False
        if not context:
            context = {}
        context['calc_taxes_done'] = True
        return super(account_invoice, self).button_reset_taxes(cr, uid, ids, context=context)

#    _columns = { 'manual_tax': fields.boolean('Handmatige Tax'),
#               }

account_invoice() 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
