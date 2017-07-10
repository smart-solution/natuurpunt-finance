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

class account_invoice(osv.osv):

    _inherit = 'account.invoice'

    def onchange_partner_id(self, cr, uid, ids, type, partner_id,\
                 date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):

        result = super(account_invoice,self).onchange_partner_id(cr, uid, ids, type, partner_id,\
                 date_invoice, payment_term, partner_bank_id, company_id)

        if partner_id:
            customer = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if not customer.is_company:
                result['value']['is_company_with_contact'] = False
            else:
                if not customer.child_ids:
                    result['value']['is_company_with_contact'] = False
                else:
                    result['value']['is_company_with_contact'] = True
            result['value']['customer_contact_id'] = False
            result['value']['use_company_address'] = False

        return result

    def onchange_customer_contact_id(self, cr, uid, ids, customer_company_id):
        """
        Reset the flag
        """
        result = {'value':{}}
        result['value']['use_company_address'] = False
        return result

    _columns = {
        'customer_contact_id': fields.many2one('res.partner', 'Contact'),
        'use_company_address': fields.boolean('Gebruik bedrijfsadres'),
        'is_company_with_contact': fields.boolean('Is company with contact'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
