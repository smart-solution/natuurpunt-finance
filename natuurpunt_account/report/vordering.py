# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import time
from openerp.report import report_sxw
from natuurpunt_tools import report

class account_invoice(report.natuurpunt_contact_rml_parse):
    def __init__(self, cr, uid, name, context):
	print "PARSER CALLED"
        super(account_vordering, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_account_number': self._get_account_number,
                                  })

    def _get_account_number(self):
        return  'IBAN BE56 2930 2120 7588'

report_sxw.report_sxw(
    'report.account.vordering',
    'account.invoice',
    'addons/natuurpunt_account/report/vordering.rml',
    parser=account_vordering
)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
