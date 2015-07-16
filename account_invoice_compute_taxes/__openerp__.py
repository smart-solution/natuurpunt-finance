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

{
    "name" : "Account Invoice Compute Taxes",
    "version" : "1.0",
    "author" : "Smart Solution (fabian.semal@smartsolution.be)",
    "category" : "Generic Modules/Account",
    "description": """
    By default, the taxes of an invoice are computed when:
        * the Compute Taxes button is pressed
        * the invoice is validated

    This module makes that the taxes are computed when the invoice is saved
""",
    "depends" : ["account"],
    "init_xml" : [
        ],
    "update_xml" : [
        'account_invoice_compute_taxes_view.xml',
        ],
    "active": False,
    "installable": True
}
