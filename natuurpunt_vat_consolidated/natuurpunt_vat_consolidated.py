from osv import osv
from osv import fields
from openerp.tools.translate import _
from collections import Counter
import base64
from datetime import date
from dateutil.relativedelta import relativedelta

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'vat_quarterly': fields.boolean("BTW per kwartaal"),
    }

res_company()

class natuurpunt_vat_consolidated(osv.osv_memory):
    _name = 'natuurpunt.vat.consolidated'
    _description = 'natuurpunt vat consolidated'

    def _get_account_period(self, cr, uid, context=None):
        res = []
        company_ids = self.pool.get('res.company').search(cr, uid,[('parent_id', '=', False), ], context=context)
        domain = [('company_id', 'in', company_ids),('special','=',False),]
        ids = self.pool.get('account.period').search(cr, uid, [('company_id', 'in', company_ids), ], context=context)
        for account_period in self.pool.get('account.period').browse(cr, uid, ids, context=context):
             res.append((account_period.id, account_period.code))
        return res

    def _get_xml_data(self, cr, uid, context=None):
        if context.get('file_save', False):
            return base64.encodestring(context['file_save'].encode('utf8'))

    _columns = {
         'name': fields.char('File Name', size=32),
         'period': fields.selection(_get_account_period, string='Jaar'),
         'msg': fields.text('File created', size=64, readonly=True),
         'file_save': fields.binary('Save File'),
         'comments': fields.text('Comments'),
    }

    _defaults = {
        'msg': 'Save the file with '".xml"' extension.',
        'file_save': _get_xml_data,
        'name': 'vat_declaration.xml',
    }

    def create_xml(self, cr, uid, ids, context=None):
        obj_tax_code = self.pool.get('account.tax.code')
        obj_acc_period = self.pool.get('account.period')
        obj_user = self.pool.get('res.users')
        obj_partner = self.pool.get('res.partner')
        mod_obj = self.pool.get('ir.model.data')
        obj_company = self.pool.get('res.company')

        if context is None:
            context = {}

        data = self.browse(cr, uid, ids[0])
        account_period_ids = [int(data.period)]
        for account_period in  obj_acc_period.browse(cr,uid, account_period_ids, context=context):
            period = {
                'date_start': account_period.date_start,
                'date_stop': account_period.date_stop,
                'month': str(account_period.date_start[5:7]),
                'year': str(account_period.date_stop[:4]),
            }

        list_of_tags = ['00','01','02','03','44','45','46','47','48','49','54','55','56','57','59','61','62','63','64','71','72','81','82','83','84','85','86','87','88','91']
        consolidation_company_ids = obj_company.search(cr, uid,[('parent_id', '=', False), ], context=context)

        for company in obj_company.browse(cr, uid, consolidation_company_ids, context=context):
            vat_no = company.partner_id.vat
            if not vat_no:
                raise osv.except_osv(_('Insufficient Data!'), _('No VAT number associated with your company.'))
            if not company.email:
                raise osv.except_osv(_('Insufficient Data!'),_('No email address associated with the company.'))
            if not company.phone:
                raise osv.except_osv(_('Insufficient Data!'),_('No phone associated with the company.'))
            vat_no.replace(' ','').upper()
            vat = vat_no[2:]
            comments = data['comments'] or ''
            send_ref = str(company.partner_id.id) + period['month'] + period['year']
            starting_month = period['month']
            ending_month = period['month']
            quarter = ((int(starting_month) - 1) / 3) + 1
            file_data = {
                        'issued_by': 'BE',
                        'vat_no': vat_no,
                        'only_vat': vat,
                        'cmpny_name': company.name,
                        'address': "%s" % company.street,
                        'post_code': company.zip,
                        'city': company.city,
                        'country_code': company.country_id.code,
                        'email': company.email,
                        'phone': company.phone.replace('.','').replace('/','').replace('(','').replace(')','').replace(' ',''),
                        'send_ref': send_ref,
                        'quarter': str(quarter),
                        'month': period['month'],
                        'year': period['year'],
                        'client_nihil': 'NO',
                        'ask_restitution': 'NO',
                        'ask_payment': 'NO',
                        'comments': comments,
                     }

        company_ids = obj_company.search(cr, uid,[('parent_id', '!=', False), ], context=context)
        account_tax_code_ids = obj_tax_code.search(cr, uid,[('company_id','in',company_ids),('parent_id','=',False)], context=context)
        tax_counter = Counter()
        for account_tax_code in obj_tax_code.browse(cr, uid, account_tax_code_ids, context=context):
            if not account_tax_code.company_id.vat_quarterly:
                code_domain = [
                    ('date_start','=',period['date_start']),
                    ('date_stop','=',period['date_stop']),
                    ('special','=',False)
                ]
            elif int(starting_month) % 3 == 0:
                code_domain = [
                    ('date_start','>=',str(date(int(period['year']),int(period['month']),1)+relativedelta(months=-2))),
                    ('date_stop','<=',period['date_stop']),
                    ('special','=',False)
                ]
            else:
                continue
            tax_code_ids = obj_tax_code.search(cr, uid, [('parent_id','child_of',account_tax_code.id)], context=context)
            account_period_domain = code_domain + [('company_id','=',account_tax_code.company_id.id)]
            account_period_ids = obj_acc_period.search(cr, uid, account_period_domain, context=context)
            for account_period in obj_acc_period.browse(cr,uid, account_period_ids, context=context):
                ctx = context.copy()
                ctx['period_id'] = account_period.id
                for tax_code in obj_tax_code.read(cr, uid, tax_code_ids, ['code','sum_period'], context=ctx):
                    tax_counter[tax_code['code']] += tax_code['sum_period']
        tax_info = [{'code': code, 'sum_period': sum_period} for code, sum_period in tax_counter.items()]

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
            if item['code'] and item['sum_period']:
                if item['code'] == 'VI':
                    if item['sum_period'] >= 0:
                        item['code'] = '71'
                    else:
                        item['code'] = '72'
                if item['code'] in list_of_tags:
                    cases_list.append(item)
        cases_list.sort()
        for item in cases_list:
            grid_amount_data = {
                    'code': str(int(item['code'])),
                    'amount': '%.2f' % abs(item['sum_period']),
                    }
            data_of_file += '\n\t\t\t<ns2:Amount GridNumber="%(code)s">%(amount)s</ns2:Amount''>' % (grid_amount_data)

        data_of_file += '\n\t\t</ns2:Data>'
        data_of_file += '\n\t\t<ns2:ClientListingNihil>%(client_nihil)s</ns2:ClientListingNihil>' % (file_data)
        data_of_file += '\n\t\t<ns2:Ask Restitution="%(ask_restitution)s" Payment="%(ask_payment)s"/>' % (file_data)
        data_of_file += '\n\t\t<ns2:Comment>%(comments)s</ns2:Comment>' % (file_data)
        data_of_file += '\n\t</ns2:VATDeclaration> \n</ns2:VATConsignment>'
        model_data_ids = mod_obj.search(cr, uid,[('model','=','ir.ui.view'),('name','=','natuurpunt_view_vat_consolidated_save_form')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        context['file_save'] = data_of_file
        return {
            'name': _('Save XML For Vat declaration'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'natuurpunt.vat.consolidated',
            'views': [(resource_id,'form')],
            'view_id': 'natuurpunt_view_vat_consolidated_save_form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

