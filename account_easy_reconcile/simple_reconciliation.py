# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2012-2013 Camptocamp SA (Guewen Baconnier)
#    Copyright (C) 2010   Sébastien Beau
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

from openerp.osv.orm import AbstractModel, TransientModel


class easy_reconcile_simple(AbstractModel):

    _name = 'easy.reconcile.simple'
    _inherit = 'easy.reconcile.base'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = None
    _key_field2 = None

    def rec_auto_lines_simple(self, cr, uid, rec, lines, context=None):
        if context is None:
            context = {}

        if self._key_field is None:
            raise ValueError("_key_field has to be defined")

        count = 0
        res = []
        while (count < len(lines)):
            for i in xrange(count+1, len(lines)):
                writeoff_account_id = False
                if self._key_field2:
#                    print "KEY2"
                    if lines[count][self._key_field] != lines[i][self._key_field] or lines[count][self._key_field2] != lines[i][self._key_field2]:
#                        print "KEY2 BREAK"
                        break
                else:
                    if lines[count][self._key_field] != lines[i][self._key_field]:
                        break

#                print "A1:",lines[count][self._key_field]
#                print "A2:",lines[i][self._key_field]
#                print "B1:",lines[count][self._key_field2]
#                print "B2:",lines[i][self._key_field2]
                check = False
                if lines[count]['credit'] > 0 and lines[i]['debit'] > 0:
                    credit_line = lines[count]
                    debit_line = lines[i]
                    check = True
                elif lines[i]['credit'] > 0  and lines[count]['debit'] > 0:
                    credit_line = lines[i]
                    debit_line = lines[count]
                    check = True
                if not check:
                    continue

                print "FOUND MATCH"

                reconciled, dummy = self._reconcile_lines(
                    cr, uid, rec, [credit_line, debit_line],
                    allow_partial=False, context=context)
                if reconciled:
                    res += [credit_line['id'], debit_line['id']]
                    del lines[i]
                    break
            count += 1
        return res, []  # empty list for partial, only full rec in "simple" rec

    def _simple_order(self, rec, *args, **kwargs):
        if self._key_field2:
            return "ORDER BY account_move_line.%s,account_move_line.%s"%(self._key_field, self._key_field2)
        return "ORDER BY account_move_line.%s" % self._key_field

    def _action_rec(self, cr, uid, rec, context=None):
        """Match only 2 move lines, do not allow partial reconcile"""
        select = self._select(rec)
        select += ", account_move_line.%s " % self._key_field
        where, params = self._where(rec)
        where += " AND account_move_line.%s IS NOT NULL " % self._key_field
        if self._key_field2:
            where += " AND account_move_line.%s IS NOT NULL " % self._key_field2

        where2, params2 = self._get_filter(cr, uid, rec, context=context)
        query = ' '.join((
            select,
            self._from(rec),
            where, where2,
            self._simple_order(rec)))
        print "QUERY:",query

        cr.execute(query, params + params2)
        lines = cr.dictfetchall()
        print "LINES:",len(lines)
        return self.rec_auto_lines_simple(cr, uid, rec, lines, context)


class easy_reconcile_simple_name(TransientModel):

    _name = 'easy.reconcile.simple.name'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
#    _key_field = 'name'
    _key_field = 'ref'
    _key_field2 = 'partner_id'

class easy_reconcile_simple_partner(TransientModel):

    _name = 'easy.reconcile.simple.partner'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'partner_id'


class easy_reconcile_simple_reference(TransientModel):

    _name = 'easy.reconcile.simple.reference'
    _inherit = 'easy.reconcile.simple'

    # has to be subclassed
    # field name used as key for matching the move lines
    _key_field = 'ref'

