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

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'company_registration_number': fields.char('company registration number', len=10),
    }

    def onchange_vat(self, cr, uid, ids, vat, context=None):
        res = {}
        res['vat_subjected'] = False
        if isinstance(vat, basestring) and vat[:2].upper() == "BE":
            res['vat_subjected'] = True
            res['company_registration_number'] = vat[2:]
        return {'value':res}

res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
