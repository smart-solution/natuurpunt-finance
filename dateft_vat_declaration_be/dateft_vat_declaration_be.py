# -*- encoding: utf-8 -*-

from mx import DateTime
import re, time, random
from openerp.tools.translate import _

from openerp.osv import fields, osv

class account_tax_code(osv.osv):
    _inherit = 'account.tax.code'

    def _sum_period_ft(self, cr, uid, ids, name, args, context):
        if context is None:
            context = {}
        move_state = ('posted', )
        if context.get('state', False) == 'all':
            move_state = ('draft', 'posted', )
        if context.get('period_id', False):
            period_id = context['period_id']
            period_to_id = context['period_to_id']
        else:
            ctx = dict(context, account_period_prefer_normal=True)
            period_id = self.pool.get('account.period').find(cr, uid, context=ctx)
            if not period_id:
                return dict.fromkeys(ids, 0.0)
            period_id = period_id[0]
            period_to_id = self.pool.get('account.period').find(cr, uid, context=ctx)
            if not period_to_id:
                return dict.fromkeys(ids, 0.0)
            period_to_id = period_to_id[0]
        return self._sum(cr, uid, ids, name, args, context,
                where=' AND line.period_id>=%s AND line.period_id<=%s AND move.state IN %s', where_params=(period_id, period_to_id, move_state))

    _columns = {
        'sum_period_ft': fields.function(_sum_period_ft, string="Period FT Sum"),
    }

account_tax_code()

class l10n_be_vat_declaration(osv.osv_memory):
    _inherit = "l1on_be.vat.declaration"

    _columns = {
        'period_to_id': fields.many2one('account.period','Period', required=True),
    }

    def create_xml(self, cr, uid, ids, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_acc_period = self.pool.get('account.period')
        obj_user = self.pool.get('res.users')
        obj_partner = self.pool.get('res.partner')
        mod_obj = self.pool.get('ir.model.data')

        if context is None:
            context = {}

        list_of_tags = ['00','01','02','03','44','45','46','47','48','49','54','55','56','57','59','61','62','63','64','71','72','81','82','83','84','85','86','87','88','91']
        data_tax = self.browse(cr, uid, ids[0])
        if data_tax.tax_code_id:
            obj_company = data_tax.tax_code_id.company_id
        else:
            obj_company = obj_user.browse(cr, uid, uid, context=context).company_id
        vat_no = obj_company.partner_id.vat
        if not vat_no:
            raise osv.except_osv(_('Insufficient Data!'), _('No VAT number associated with your company.'))
        vat_no = vat_no.replace(' ','').upper()
        vat = vat_no[2:]

        tax_code_ids = obj_tax_code.search(cr, uid, [('parent_id','child_of',data_tax.tax_code_id.id), ('company_id','=',obj_company.id)], context=context)
        ctx = context.copy()
        data  = self.read(cr, uid, ids)[0]
        ctx['period_id'] = data['period_id'][0]
        ctx['period_to_id'] = data['period_to_id'][0]
        tax_info = obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period_ft'], context=ctx)

        default_address = obj_partner.address_get(cr, uid, [obj_company.partner_id.id])
        default_address_id = default_address.get("default", obj_company.partner_id.id)
        address_id= obj_partner.browse(cr, uid, default_address_id, context)

        account_period = obj_acc_period.browse(cr, uid, data['period_id'][0], context=context)
        if not data['period_to_id'][0]:
            account_period_to = obj_acc_period.browse(cr, uid, data['period_id'][0], context=context)
        else:
            account_period_to = obj_acc_period.browse(cr, uid, data['period_to_id'][0], context=context)
        issued_by = vat_no[:2]
        comments = data['comments'] or ''

        send_ref = str(obj_company.partner_id.id) + str(account_period.date_start[5:7]) + str(account_period_to.date_stop[:4])

        starting_month = account_period.date_start[5:7]
        ending_month = account_period_to.date_stop[5:7]
        quarter = str(((int(starting_month) - 1) / 3) + 1)

        if not address_id.email:
            raise osv.except_osv(_('Insufficient Data!'),_('No email address associated with the company.'))
        if not address_id.phone:
            raise osv.except_osv(_('Insufficient Data!'),_('No phone associated with the company.'))
        file_data = {
                        'issued_by': issued_by,
                        'vat_no': vat_no,
                        'only_vat': vat_no[2:],
                        'cmpny_name': obj_company.name,
                        'address': "%s %s"%(address_id.street or "",address_id.street2 or ""),
                        'post_code': address_id.zip or "",
                        'city': address_id.city or "",
                        'country_code': address_id.country_id and address_id.country_id.code or "",
                        'email': address_id.email or "",
                        'phone': address_id.phone.replace('.','').replace('/','').replace('(','').replace(')','').replace(' ',''),
                        'send_ref': send_ref,
                        'quarter': quarter,
                        'month': starting_month,
                        'year': str(account_period_to.date_stop[:4]),
                        'client_nihil': (data['client_nihil'] and 'YES' or 'NO'),
                        'ask_restitution': (data['ask_restitution'] and 'YES' or 'NO'),
                        'ask_payment': (data['ask_payment'] and 'YES' or 'NO'),
                        'comments': comments,
                     }

        data_of_file = """<?xml version="1.0"?>
<ns2:VATConsignment xmlns="http://www.minfin.fgov.be/InputCommon" xmlns:ns2="http://www.minfin.fgov.be/VATConsignment" VATDeclarationsNbr="1">
    <ns2:Representative>
        <RepresentativeID identificationType="NVAT" issuedBy="%(issued_by)s">%(only_vat)s</RepresentativeID>
        <Name>%(cmpny_name)s</Name>
        <Street>%(address)s</Street>
        <PostCode>%(post_code)s</PostCode>
        <City>%(city)s</City>
        <CountryCode>%(country_code)s</CountryCode>
        <EmailAddress>%(email)s</EmailAddress>
        <Phone>%(phone)s</Phone>
    </ns2:Representative>
    <ns2:VATDeclaration SequenceNumber="1" DeclarantReference="%(send_ref)s">
        <ns2:Declarant>
            <VATNumber xmlns="http://www.minfin.fgov.be/InputCommon">%(only_vat)s</VATNumber>
            <Name>%(cmpny_name)s</Name>
            <Street>%(address)s</Street>
            <PostCode>%(post_code)s</PostCode>
            <City>%(city)s</City>
            <CountryCode>%(country_code)s</CountryCode>
            <EmailAddress>%(email)s</EmailAddress>
            <Phone>%(phone)s</Phone>
        </ns2:Declarant>
        <ns2:Period>
    """ % (file_data)

        if starting_month != ending_month:
            #starting month and ending month of selected period are not the same
            #it means that the accounting isn't based on periods of 1 month but on quarters
            data_of_file += '\t\t<ns2:Quarter>%(quarter)s</ns2:Quarter>\n\t\t' % (file_data)
        else:
            data_of_file += '\t\t<ns2:Month>%(month)s</ns2:Month>\n\t\t' % (file_data)
        data_of_file += '\t<ns2:Year>%(year)s</ns2:Year>' % (file_data)
        data_of_file += '\n\t\t</ns2:Period>\n'
        data_of_file += '\t\t<ns2:Data>\t'
        cases_list = []
        for item in tax_info:
            if item['code'] == '91' and ending_month != 12:
                #the tax code 91 can only be send for the declaration of December
                continue
            if item['code'] and item['sum_period_ft']:
                if item['code'] == 'VI':
                    if item['sum_period_ft'] >= 0:
                        item['code'] = '71'
                    else:
                        item['code'] = '72'
                if item['code'] in list_of_tags:
                    cases_list.append(item)
        cases_list.sort()
        for item in cases_list:
            grid_amount_data = {
                    'code': str(int(item['code'])),
                    'amount': '%.2f' % abs(item['sum_period_ft']),
                    }
            data_of_file += '\n\t\t\t<ns2:Amount GridNumber="%(code)s">%(amount)s</ns2:Amount''>' % (grid_amount_data)

        data_of_file += '\n\t\t</ns2:Data>'
        data_of_file += '\n\t\t<ns2:ClientListingNihil>%(client_nihil)s</ns2:ClientListingNihil>' % (file_data)
        data_of_file += '\n\t\t<ns2:Ask Restitution="%(ask_restitution)s" Payment="%(ask_payment)s"/>' % (file_data)
        data_of_file += '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>' % (file_data)
        data_of_file += '\n\t</ns2:VATDeclaration> \n</ns2:VATConsignment>'
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','view_vat_save')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context['file_save'] = data_of_file
        return {
            'name': _('Save XML For Vat declaration'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'l1on_be.vat.declaration',
            'views': [(resource_id,'form')],
            'view_id': 'view_vat_save',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

l10n_be_vat_declaration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
