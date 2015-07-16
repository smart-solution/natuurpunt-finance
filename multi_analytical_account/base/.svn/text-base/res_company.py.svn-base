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

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'dimension_id': fields.one2many('account.analytic.dimension', 'company_id', 'Analytical Dimension'),
        'invoice_logo': fields.binary('Invoice Logo'),
    }
res_company()

class account_analytic_dimension(osv.osv):
    _name = 'account.analytic.dimension'
    _order = 'sequence'
    _columns = {
        'company_id': fields.many2one('res.company', 'Company'),
        'name': fields.char('Name', size=256),
        'sequence': fields.integer('Sequence')
    }

account_analytic_dimension()
