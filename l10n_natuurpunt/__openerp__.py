# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
##############################################################################
#    Module programed and financed by:
#    Vauxoo, C.A. (<http://vauxoo.com>).
#    Our Community team mantain this module:
#    https://launchpad.net/~openerp-venezuela
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name' : 'Natuurpunt - Accounting',
    'version': '1.0',
    'author': ['Smart Solution'],
    'category': 'Localization/Account Charts',
    'description':
"""""",
    'depends': ['account',
                'base_vat', 
                'account_chart','l10n_be'
    ],
    'demo': [],
    'data': [
#        'data/account_financial_report.xml',
#             'account_pcmn_belgium.xml',
#             'data/account_tax_code_template.xml',
#             'data/account_user_types.xml',
#             'data/Boekhoudplan_CON_NP.xml',
#             'data/account_chart.xml',
#             'data/account_tax_template.xml',
        'wizard/l10n_be_account_vat_declaration_view.xml',
        'wizard/l10n_be_vat_intra_view.xml',
        'wizard/l10n_be_partner_vat_listing.xml',
#        'wizard/account_wizard.xml',
#             'data/fiscal_templates.xml',
#             'data/account_fiscal_position_tax_template.xml',
    ],
    'auto_install': False,
    'installable': True,
    'images': [],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

