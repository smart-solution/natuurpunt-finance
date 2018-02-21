# -*- coding: utf-8 -*-
##############################################################################
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
    "name" : "natuurpunt_account_mail",
    "version" : "1.0",
    "author" : "Natuurpunt (joeri.belis@natuurpunt.be)",
    "website" : "www.natuurpunt.be",
    "category" : "Accountancy",
    "description": """
    Custom mail support for natuurpunt account 
""",
    "depends" : ["natuurpunt_account","natuurpunt_purchase_mail"],
    "data" : ["natuurpunt_account_mail_view.xml",
              "edi/natuurpunt_vordering_template.xml",
              "edi/natuurpunt_onkostennota_template.xml"],
    "init_xml" : [],
    "update_xml" : [],
    "active": False,
    "installable": True
}
