# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    
#    Copyright (c) 2013 Noviat nv/sa (www.noviat.be). All rights reserved.
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

from datetime import datetime, date, timedelta
from lxml import etree
from openerp.osv import osv, fields
from tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class payment_order_create(osv.osv_memory):
    _inherit = 'payment.order.create'

    _defaults = {
        'duedate': lambda *a: (date.today() + timedelta(30)).isoformat(),
    }

    def journal_domain(self, cr, uid, context=None):
        """
        override this method in order to customise the journals to search on
        """
        journal_domain = [('journal_id.type', 'in', ['purchase', 'sale_refund', 'general', 'situation'])]
        return journal_domain
    
    def search_entries(self, cr, uid, ids, context=None):
        """
        Override the search_entries & fields_view_get methods of the account_payment payment.order.create object
        """        
        line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        search_due_date = data['duedate']
        # Search for move line to pay:
        domain = [('reconcile_id', '=', False), ('partner_id', '!=', False), ('account_id.type', 'in', ['payable', 'receivable']), ('amount_to_pay', '>', 0)]  # update Noviat
        domain = domain + ['|', ('date_maturity', '<=', search_due_date), ('date_maturity', '=', False)]
        journal_domain = self.journal_domain(cr, uid)
        domain = domain + journal_domain
        line_ids = line_obj.search(cr, uid, domain, context=context)
        context.update({'line_ids': line_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_create_payment_order_lines')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']  
        return {'name': _('Populate Payment'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.order.create',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
        }
        
    """
    add context to 'entries' field for use in account.move.line
    """
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(payment_order_create, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        if context and 'line_ids' in context and view_type == 'form':
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='entries']")
            for node in nodes:
                # add context for use in account.move.line
                node.set('context', "{'account_payment':'1', 'view_mode':'tree'}")
                node.set('colspan', '4')
                node.set('height', '300')
                node.set('width', '800')
            res['arch'] = etree.tostring(doc)
        return res
    
    def create_payment(self, cr, uid, ids, context=None):
        """
        This method replaces the original one for multi-currency purposes
        """
        order_obj = self.pool.get('payment.order')
        line_obj = self.pool.get('account.move.line')
        payment_obj = self.pool.get('payment.line')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        line_ids = [entry.id for entry in data.entries]
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        payment = order_obj.browse(cr, uid, context['active_id'], context=context)
        t = payment.mode.type == 'iso20022' and payment.mode.id or None
        line2bank = line_obj.line2bank(cr, uid, line_ids, t, context)

        company_currency = payment.mode.company_id.currency_id
        payment_mode_currency = payment.mode.journal.currency or company_currency

        ## Finally populate the current payment with new lines:
        for line in line_obj.browse(cr, uid, line_ids, context=context):
            if payment.date_prefered == "now":
                #no payment date => immediate payment
                date_to_pay = False
            elif payment.date_prefered == 'due':
                date_to_pay = line.date_maturity
            elif payment.date_prefered == 'fixed':
                date_to_pay = payment.date_scheduled

            transaction_currency = line.currency_id or company_currency
            if transaction_currency != payment_mode_currency and payment.mode.type == 'iso20022':
                raise osv.except_osv(_('Unsupported Operation !'), 
                    _("The payment in another currency as the originating transaction is not supported in the" \
                      "current release of the ISO 20022 Payment Gateway"
                      "\nTransaction Currency: %s, Payment Mode Currency: %s)"   \
                      "\n\nPlease contact info@noviat.be if this is a requirement.") 
                    %(transaction_currency, payment_mode_currency) )
                                   
            payment_obj.create(cr, uid,{
                    'move_line_id': line.id,
                    'amount_currency': line.amount_to_pay,
                    'bank_id': line2bank.get(line.id),
                    'order_id': payment.id,
                    'partner_id': line.partner_id and line.partner_id.id or False,
                    'communication': line.ref or '/',
                    'date': date_to_pay,
                    'currency': line.currency_id.id or company_currency.id,
                }, context=context)
        return {'type': 'ir.actions.client', 'tag': 'reload',}
    
payment_order_create()
