# -*- coding: utf-8 -*-
##############################################################################
#
#    Natuurpunt VZW
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

class account_move_line(osv.osv):
    _name = 'account.move.line'
    _inherit = 'account.move.line'
    
    def _get_reconcile(self, cr, uid, ids,name, unknow_none, context=None):
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            if line.reconcile_id:
                res[line.id] = str(line.reconcile_id.name)
            elif line.reconcile_partial_id:
                res[line.id] = str(line.reconcile_partial_id.name)
        return res

#    _columns = {
#        'reconcile': fields.function(_get_reconcile, type='char', string='Reconcile Ref', store=True),
#     }
    
    _columns = {
         'reconcile': fields.function(
                     _get_reconcile, type='char', string='Reconcile Ref', store={
             'account.move.line': (lambda self, cr, uid, ids, c={}: ids, ['reconcile_id'], 10),
             }),

     }


account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: