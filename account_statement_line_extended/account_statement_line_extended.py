#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
# 
##############################################################################

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp



BULK_SIZE = 5

class account_bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    bulk_state = 1

    def create_move_from_st_line(self, cr, uid, st_line_id, company_currency_id, st_line_number, context=None):
        """
        Commit after each bulk of statement lines
        """
        res = super(account_bank_statement, self).create_move_from_st_line(cr, uid, st_line_id, company_currency_id, st_line_number, context=context)

        if self.bulk_state == BULK_SIZE:
            cr.commit()
            self.bulk_state = 1
        else:
            self.bulk_state += 1

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
