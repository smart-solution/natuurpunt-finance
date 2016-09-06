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

class wizard_account_move_line_invoices(osv.osv_memory):

    _name = 'wizard.account.move.line.invoices'

    def invoices_find(self, cr, uid, ids, context=None):
        """Find the related invoices"""
        invoice_ids = []
        for line in self.pool.get('account.move.line').browse(cr, uid, context['active_ids']):
            invoice = self.pool.get('account.invoice').search(cr, uid, [('journal_id','=',line.journal_id.id),('number','=',line.move_id.name)])
            if invoice:
                invoice_ids.append(invoice[0])
        mod_obj = self.pool.get('ir.model.data')

        try:
            tree_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_tree')[1]
        except ValueError:
            tree_view_id = False
        try:
            form_view_id = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')[1]
        except ValueError:
            form_view_id = False

        return {'name': _('Journal Items Invoices'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'views': [(tree_view_id, 'tree'), (form_view_id, 'form')],
                'type': 'ir.actions.act_window',
                'domain': [('id','in',invoice_ids)]
        }


class account_bank_statement_line(osv.osv):

    _inherit = 'account.bank.statement.line'

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        res = super(account_bank_statement_line, self).onchange_partner_id(cr, uid, ids, partner_id, context=context)
        line = self.browse(cr, uid, ids)
        if line and line[0].account_id and partner_id:
            del res['value']['account_id']
        return res 


# v:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
