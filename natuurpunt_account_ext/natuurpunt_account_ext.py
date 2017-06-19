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
from openerp import netsvc
from openerp.tools.translate import _
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp
from natuurpunt_tools import create_xml, create_node, transform,get_approval_state
from natuurpunt_tools import sum_groupby
from itertools import groupby

class account_invoice(osv.osv):

    _inherit = 'account.invoice'

    def _reconciled(self, cr, uid, ids, name, args, context=None):
        res = {}
        wf_service = netsvc.LocalService("workflow")
        for inv in self.browse(cr, uid, ids, context=context):
            res[inv.id] = self.test_paid(cr, uid, [inv.id])
            if not res[inv.id] and inv.state == 'paid':
                state = get_approval_state(self, cr, uid, inv, context = context)
                if state == 'waiting' or state == 'approved':
                    if state == 'waiting':
                        state = 'confirmed'
                    self.write(cr, uid, ids, {'state': state}, context=context)
                else:
                    wf_service.trg_validate(uid, 'account.invoice', inv.id, 'open_test', cr)
                
        return res
    
    def _get_invoice_from_reconcile(self, cr, uid, ids, context=None):
        move = {}
        for r in self.pool.get('account.move.reconcile').browse(cr, uid, ids, context=context):
            for line in r.line_partial_ids:
                move[line.move_id.id] = True
            for line in r.line_id:
                move[line.move_id.id] = True

        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids

    def _get_invoice_from_line(self, cr, uid, ids, context=None):
        move = {}
        for line in self.pool.get('account.move.line').browse(cr, uid, ids, context=context):
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    move[line2.move_id.id] = True
            if line.reconcile_id:
                for line2 in line.reconcile_id.line_id:
                    move[line2.move_id.id] = True
        invoice_ids = []
        if move:
            invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('move_id','in',move.keys())], context=context)
        return invoice_ids
    
    def _store_set_values(self, cr, uid, ids, fields, context=None):
        """force multi function_field 'amount_total_signed' to use the _amount_all function
        of the inherited account_invoice class
        """        
        return super(account_invoice, self)._store_set_values(
                cr, uid, ids, 
                sorted(fields, key = lambda x: 0 if x=='amount_total_signed' else 1), context)
 
    def _amount_all(self, cr, uid, ids, name, args, context=None):
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
                'amount_total_signed': 0.0
            }
            for line in invoice.invoice_line:
                res[invoice.id]['amount_untaxed'] += line.price_subtotal
            for line in invoice.tax_line:
                res[invoice.id]['amount_tax'] += line.amount
            res[invoice.id]['amount_total'] = res[invoice.id]['amount_tax'] + res[invoice.id]['amount_untaxed']

            sign = -1 if invoice.type in ['in_refund','out_refund'] else 1
            res[invoice.id]['amount_total_signed'] = res[invoice.id]['amount_total'] * sign
        return res

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()

    _columns = {
        'amount_total_signed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Totaal (+/-)',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line, ['price_unit','invoice_line_tax_id','quantity','discount','invoice_id'], 20),
            },
            multi='all'),
        'reconciled': fields.function(_reconciled, string='Paid/Reconciled', type='boolean',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids, None, 50), # Check if we can remove ?
                'account.move.line': (_get_invoice_from_line, None, 50),
                'account.move.reconcile': (_get_invoice_from_reconcile, None, 50),
            }, help="It indicates that the invoice has been paid and the journal entry of the invoice has been reconciled with one or several journal entries of payment."),
    }

    def create(self, cr, uid, vals, context=None):
        """Do not allow to create an invoice for an unactive partner"""
        if 'partner_id' in vals and vals['partner_id']:
            partner = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'])
            print "ACTIVE:",partner.active
            if not partner.active:
                raise osv.except_osv(_('Error!'), _('You cannot create an invoice for an unactive partner.'))
    
        return super(account_invoice, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        """Do not allow to create an invoice for an unactive partner"""
        if 'partner_id' in vals and vals['partner_id']:
            partner = self.pool.get('res.partner').browse(cr, uid, vals['partner_id'])
            if not partner.active:
                raise osv.except_osv(_('Error!'), _('You cannot create an invoice for an unactive partner.'))
    
        return super(account_invoice, self).write(cr, uid, ids, vals, context=context)

    def toxml(self, cr, uid, ids, context=None):
        """
        xml-ifies account.invoice
        put here the bussiness logic to get all the invoice data
        into a dict per node.
        """

        def taxes(invoice_id):
            tax_per_line = []
            tax_lines = self.pool.get('account.invoice.tax').search(cr, uid, [('invoice_id','=',invoice_id)])
            if not tax_lines:
                return tax_per_line
            for line in self.pool.get('account.invoice.tax').browse(cr, uid, tax_lines):
                tax_per_line.append(
                    {'line_id':line.invoice_line_id.id,
                     'name':line.name,
                     'amount':line.amount,
                     'base':line.base,
                     'percent':line.tax_id.amount*100})
            return tax_per_line

        for invoice in self.browse(cr, uid, ids, context=context):
            vzw = self.pool.get('res.partner').browse(cr, uid, invoice.company_id.id)
            partner = self.pool.get('res.partner').browse(cr, uid, invoice.partner_id.id)
            edi_xml = filter(None,map(lambda x: x if x.document_type == invoice.type else None,partner.edi_xml_ids))
            if not edi_xml:
                raise osv.except_osv(_('Error!'), _('partner has no EDI configured for this document type.'))
            invoice_node = {
                'ID':invoice.internal_number,
                'IssueDate':invoice.date_invoice,
                'StartDate':invoice.date_invoice,
                'EndDate':invoice.date_invoice,
                'OrderReference':invoice.name if invoice.name else '',
                'PaymentDueDate':invoice.date_due,
                'InstructionNote':invoice.reference,
                'TaxAmount':invoice.amount_untaxed,
                'LineExtensionAmount':invoice.amount_untaxed,
                'TaxExclusiveAmount':invoice.amount_untaxed,
                'TaxInclusiveAmount':invoice.amount_total,
                'PayableAmount':invoice.amount_total,
            }
            accounting_supplier_party_node = {
                'ID':invoice.company_id.company_registry,
                'Name':vzw.name,
                'StreetName':vzw.street,
                'CityName':vzw.city,
                'PostalZone':vzw.zip,
                'RegistrationName':vzw.name,
                'CompanyID':vzw.vat,
                'Telephone':vzw.phone if vzw.phone else '',
                'ElectronicMail':vzw.email if vzw.email else '',
            }
            accounting_customer_party_node = {
                'ID':partner.company_registration_number,
                'Name':partner.name,
                'StreetName':partner.street,
                'CityName':partner.city,
                'PostalZone':partner.zip,
                'Country':partner.country_id.code,
                'CompanyID':partner.vat,
                'Telephone':partner.phone if partner.phone else '',
                'ElectronicMail':partner.email if partner.email else '',
            }
            delivery_node = {
                'StreetName':accounting_customer_party_node['StreetName'],
                'CityName':accounting_customer_party_node['CityName'],
                'PostalZone':accounting_customer_party_node['PostalZone'],
                'Country':accounting_customer_party_node['Country'],
            }
            def invoiceline_node(line):
                line_tax = next((item for item in tax_per_line if item.get('line_id') and item['line_id'] == line.id),None)
                return {
                    'InvoicedQuantity':line.quantity,
                    'LineExtensionAmount':line.price_subtotal,
                    'Description':line.name,
                    'Name':line.name,
                    'ClassifiedTaxCategoryID':'A',
                    'Percent':line_tax['percent'] if 'percent' in line_tax else 0,
                    'PriceAmount':line.price_unit,
                }
            def tax_node(tax_name, tax):
                line_tax = next((item for item in tax_per_line if item.get('name') and item['name'] == tax_name),None)
                return {
                    'TaxableAmount':tax['base'],
                    'TaxAmount':tax['amount'],
                    'Percent':line_tax['percent'] if 'percent' in line_tax else 0,
                }

            tax_per_line = taxes(invoice.id)
            name_key = lambda x: x['name']
            tax_grouped_per_tax_name = groupby(sorted(tax_per_line,key=name_key),name_key)
            tax_summarized_per_tax_name = sum_groupby(tax_grouped_per_tax_name,['base','amount'])

            xml_data = create_xml(
                          create_node('Invoice',invoice_node,
                             create_node('AccountingSupplierParty',accounting_supplier_party_node),
                             create_node('AccountingCustomerParty',accounting_customer_party_node),
                             create_node('Delivery',delivery_node)),
                          [create_node('Tax',tax_node(tax_name, tax)) for tax_name, tax in tax_summarized_per_tax_name],
                          [create_node('InvoiceLine',invoiceline_node(line)) for line in invoice.invoice_line])
            res_xml = transform(edi_xml[0].xml, edi_xml[0].xslt, xml_data)
            print res_xml
        return True

account_invoice()

class payment_order(osv.osv):

    _inherit = 'payment.order'

    def _default_mode(self, cr, uid, context=None):
        modes = self.pool.get('payment.mode').search(cr, uid, [('type','=',4)], context=context)
        mode = False
        if len(modes) == 1:
            mode= modes[0]

        return mode

    def default_get(self, cr, uid, fields, context=None):
        """Check for required dimension"""
        if context is None:
            context = {}
        result = super(payment_order, self).default_get(cr, uid, fields, context=context)

        if 'payment_order_type' in result and result['payment_order_type'] == 'payment':
            result['mode'] = self._default_mode(cr, uid, context=context)

        return result


class res_partner_bank(osv.osv):

    _inherit = 'res.partner.bank'

    _columns = {
            'organisation_type_id': fields.related('partner_id', 'organisation_type_id',  type='many2one', relation='res.organisation.type', string='Organisation Type', readonly=False),
    }

    _defaults = {
        'state': 'iban',
        'sequence': 1,
        'organisation_type_id': lambda self, cr, uid, c: self.pool.get('res.partner').browse(cr, uid, c['default_partner_id'], c).organisation_type_id.id if 'default_partner_id' in c and c['default_partner_id'] else False,
    }


class res_partner(osv.osv):

    _inherit = 'res.partner'

    def has_something_to_reconcile(self, cr, uid, partner_id, context=None):
        '''
        Always update the last_reconciliation_date 
        '''
        return False


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
