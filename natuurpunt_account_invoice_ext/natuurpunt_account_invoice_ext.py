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
from openerp import SUPERUSER_ID

class OrganisatiePartnerEnum():
    AFDELING = 'Afdeling'
    WERKGROEP = 'Werkgroep'
    REGIONALE = 'Regionaal samenwerkingsverband'

class res_partner(osv.osv):

    _inherit = 'res.partner'

    def _fields_sync(self, cr, uid, partner, update_values, context=None):
        """
        disable syncing of VAT and other fields
        the natuurpunt implementation skips this feature of field sync
        """
        pass

    def is_penningmeester(self, cr, uid, ids, parent_id, context=None):
        res = False
        if ids:
            res_org_fnc_obj = self.pool.get('res.organisation.function')
            domain = [('partner_id', '=', parent_id),('person_id', 'in', ids)]
            res_org_fnc_ids = res_org_fnc_obj.search(cr, SUPERUSER_ID, domain)
            for function in res_org_fnc_obj.browse(cr, SUPERUSER_ID, res_org_fnc_ids, context=context):
                if function.name == 'penningmeester':
                    res = True
                    break
        return res

    def onchange_address(self, cr, uid, ids, use_parent_address, parent_id, context=None):

        result = super(res_partner,self).onchange_address(cr, uid, ids, \
                 use_parent_address, parent_id, context=context)

        if parent_id:
            parent = self.browse(cr, uid, parent_id, context=context)
            orgs = [
                OrganisatiePartnerEnum.AFDELING,
                OrganisatiePartnerEnum.WERKGROEP,
                OrganisatiePartnerEnum.REGIONALE,
            ]
            # check function of partner for org types
            if parent.organisation_type_id.name in orgs and not(self.is_penningmeester(cr, uid, ids, parent_id)):
                message = _('Contactpersoon bij %s %s kan enkel als penningmeester!'%(parent.organisation_type_id.name, parent.name))
                warning = {'title':'Error!','message':message}
                return {
                    'warning': {'title': _('Error'), 'message': message,},
                    'value': { 'parent_id': False },
                }
        return result

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
