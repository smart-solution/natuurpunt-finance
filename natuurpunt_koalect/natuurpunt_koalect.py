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

class res_koalect(osv.osv):
    _name = 'res.koalect'
    _description = 'koalect API configuration'
    _columns = {
                'name': fields.char(string="Name", size=100,),
                'url': fields.char(string="API URL", size=100, required=True),
                'key': fields.char(string="API Key", size=100, required=True), 
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
