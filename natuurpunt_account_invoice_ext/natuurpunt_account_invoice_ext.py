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

    def onchange_customer_company_id(self, cr, uid, ids, customer_company_id):
        """
        Check if the partner is a company and has contacts
        """
        result = {'value':{}}
        customer = self.pool.get('res.partner').browse(cr, uid, customer_company_id)
        if customer_company_id and not customer.is_company:
            result['value']['is_company_with_contact'] = False
        if customer_company_id and customer.is_company and not customer.child_ids:
            result['value']['is_company_with_contact'] = False
        if customer_company_id and customer.is_company and customer.child_ids:
            result['value']['is_company_with_contact'] = True
        result['value']['customer_contact_id'] = False
        result['value']['use_company_address'] = False
        result['value']['partner_id'] = False
        return result

    def onchange_customer_contact_id(self, cr, uid, ids, customer_company_id):
        """
        Reset the flag
        """
        result = {'value':{}}
        result['value']['use_company_address'] = False
        return result

    _columns = {
        'customer_company_id': fields.many2one('res.partner', 'Klant', required=True),
        'customer_contact_id': fields.many2one('res.partner', 'Contact'),
        'use_company_address': fields.boolean('Gebruik bedrijfsadres'),
        'is_company_with_contact': fields.boolean('Is company with contact'),
    }

    def create(self, cr, uid, vals, context=None):
        """
        Rules for invoicing
        """

        vals['partner_id'] = vals['customer_company_id']

        return super(account_invoice, self).create(cr, uid, vals=vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """
        Rules for invoicing
        """
        
        if 'customer_contact_id' in vals and vals['customer_contact_id']:
            vals['partner_id'] = vals['customer_company_id']
        
        if 'customer_company_id' in vals and vals['customer_company_id']:
            vals['partner_id'] = vals['customer_company_id']

        return super(account_invoice, self).write(cr, uid, ids, vals=vals, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
