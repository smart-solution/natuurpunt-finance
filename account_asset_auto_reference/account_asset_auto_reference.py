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

from osv import osv, fields

class account_asset_asset(osv.Model):

    _inherit = 'account.asset.asset'

    _columns = {
        'sequence_id': fields.many2one('ir.sequence', 'Sequence', required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        """Set / as temporary value for the asset reference"""
        if context is None:
            context = {} 
        result = super(account_asset_asset, self).default_get(cr, uid, fields, context=context)
        result['code'] = '/'

        # Find the asset sequence to use
        if 'company_id' in result and result['company_id']:
            asset_seq = self.pool.get('ir.sequence').search(cr, uid, [('company_id','=',result['company_id']), ('code','=','account.asset.ref')])
            if asset_seq:
                result['sequence_id'] = asset_seq[0] 
        return result

    def create(self, cr, uid, vals, context=None):
        """Use a sequence to generate the asset reference"""
        vals['code'] = self.pool.get('ir.sequence').next_by_id(cr, uid, vals['sequence_id'], context)
        return super(account_asset_asset, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """Use a sequence to generate the asset reference"""
        assets = self.browse(cr, uid, ids)
        for asset in assets:
            if 'sequence_id' in vals and vals['sequence_id']:
                vals['code'] = self.pool.get('ir.sequence').next_by_id(cr, uid, vals['sequence_id'], context)
        return super(account_asset_asset, self).write(cr, uid, ids, vals, context=context)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
