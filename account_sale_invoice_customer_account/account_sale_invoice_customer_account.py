#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
##############################################################################

from osv import osv, fields


class res_partner(osv.osv):

    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'property_customer_cost_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Default Revenue Account",
            view_load=True,
            domain="[('type', '=', 'other')]",
            help="This account will be used instead of the default one as the cost account for the current partner",
            required=False),

    }
res_partner()


class account_invoice_line(osv.osv):

    _name = 'account.invoice.line'
    _inherit = 'account.invoice.line'

    def default_get(self, cr, uid, fields, context=None):
        """Get the cost account from the customer"""
        res = super(account_invoice_line, self).default_get(cr, uid, fields, context=context)
        if 'type' in context and context['type'] and context['type'] == 'out_invoice':
            if 'partner_id' in context and context['partner_id']:
                partner = self.pool.get('res.partner').browse(cr, uid, context['partner_id'])
                if partner and partner.property_customer_cost_account:
                    res['account_id'] = partner.property_customer_cost_account.id
        return res

account_invoice_line()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
