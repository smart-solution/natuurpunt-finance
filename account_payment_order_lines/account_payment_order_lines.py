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
import netsvc

class wizard_account_payment_order_split(osv.osv_memory):

    _name = 'wizard.account.payment.order.split'

    def porder_split(self, cr, uid, ids, context=None):
        """split payment order"""
        wf_service = netsvc.LocalService('workflow')
        split_qty = 10000
        for porder in self.pool.get('payment.order').browse(cr, uid, context['active_ids']):
            line_ids = [line.id for line in porder.line_ids]
            line_nbr = len(line_ids)
            while line_nbr > split_qty:
                new_porder = self.pool.get('payment.order').copy(cr, uid, porder.id, {'line_ids':False}, context=context)
                new_line_ids = line_ids[:split_qty]
                line_ids = line_ids[split_qty:]
                line_nbr = len(line_ids)
                self.pool.get('payment.line').write(cr, uid, new_line_ids, {'order_id':new_porder})
                wf_service.trg_validate(uid, 'payment.order', new_porder, 'open', cr) 
        return True

#class payment.order.line(osv.osv):
#
#    _inherit = 'payment.order.line'
#
#    def invoices_pay(self, cr, uid, ids, context=None):
#        for pol in self.browse(cr, uid, ids):
#            continue

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
