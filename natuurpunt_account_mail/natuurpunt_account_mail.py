# -*- coding: utf-8 -*-
##############################################################################
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

from openerp.osv import fields, osv
import base64
import logging
from openerp import netsvc
from openerp.tools.translate import _
import json

_logger = logging.getLogger('natuurpunt_account_mail')

class account_invoice_mail_compose_message(osv.TransientModel):
    _name = 'account.invoice.mail.compose.message'
    _inherit = 'mail.compose.message'
    _description = 'Account invoice Email composition wizard'

    _columns = {
        'customer_id': fields.many2one('res.partner', string='email to customer', required=True, ),
        'report_name': fields.char('report', help="account invoice report attachment"),
        'report_size': fields.char('file size', help="account invoice report attachment"),
        'report_data': fields.binary('binary report data'),
        'store_id' : fields.char('store_id'),
        'json_object' : fields.char('json_object', help="additional emails"),
    }
    
    def sizeof_fmt(self, num, suffix='B'):
        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
            if abs(num) < 1024.0:
                return " (%3.1f%s%s) " % (num, unit, suffix)
            num /= 1024.0
        return " (%.1f%s%s) " % (num, 'Yi', suffix)
    
    def get_record_data(self, cr, uid, model, res_id, context=None):
        res = super(account_invoice_mail_compose_message, self).get_record_data(cr, uid, model, res_id, context=context)

        default_template_id = context.get('default_template_id',False)
        for account_invoice in self.pool.get(model).browse(cr, uid, [res_id], context=context):
            res['customer_id'] = account_invoice.partner_id.id
            res['partner_id'] = account_invoice.partner_id.id
            report_attachment = self.generate_report_attachment(cr, uid, account_invoice.internal_number, context=context)
            for report in report_attachment:
                res['report_name'] = report[0]
                res['report_size'] = self.sizeof_fmt(len(report[1]))
                res['report_data'] = report[1]

        for user in self.pool.get('res.users').browse(cr, uid, [uid], context=context):
            res['email_from'] = user.email_work
            ctx = dict(context)
            ctx.update({'current_user_name':user.name})
            ctx.update({'current_user_email':user.email_work})

        if default_template_id:
            for template in self.pool.get('email.template').browse(cr, uid, [default_template_id], context=context):
                res['subject'] = self.render_template(cr, uid, template.subject, model, res_id, context=ctx)
                res['body'] = self.render_template(cr, uid, template.body_html, model, res_id, context=ctx)

        return res

    def create_attachments(self, cr, uid, wizard, recipient_id, message_id, context=None):
        # convert report to attachment
        ir_attachment = self.pool.get('ir.attachment')
        invoice_sent_obj = self.pool.get('account.invoice.sent')
        attachment_ids = []
        attachment_data = {
            'name': wizard['report_name'],
            'datas_fname': wizard['report_name'],
            'db_datas': wizard['report_data'],
            'res_model': 'mail.message',
            'res_id': message_id,
            'partner_id': recipient_id,
        }

        wf_service = netsvc.LocalService('workflow')
        vals = {
            'invoice_id': context['default_res_id'],
            'name': context['service_name'],
        }
        account_invoice_sent_id = invoice_sent_obj.create(cr,uid,vals)
        wf_service.trg_validate(uid, 'account.invoice.sent', account_invoice_sent_id, 'print_pdf', cr)
        for invoice_sent in invoice_sent_obj.browse(cr,uid,[account_invoice_sent_id]):
            if invoice_sent.state == 'done':
                attachment_ids.append(invoice_sent.ir_attachment_id.id)
            else:
                raise osv.except_osv(_('Error!'),_("Probleem bij aanmaken van PDF!"))

        # get the external memory attachments
        if wizard['store_id']:
            ext_att_ids = self.pool.get('memory.ir.attachment').search(cr, uid, [('store_id', '=', wizard['store_id'])])
            for ext_att in self.pool.get('memory.ir.attachment').browse(cr, uid, ext_att_ids, context=context):
                attachment_data = {
                    'name': ext_att.filename,
                    'datas_fname': ext_att.filename,
                    'db_datas': ext_att.data,
                    'res_model': 'mail.message',
                    'res_id': message_id,
                    'partner_id': recipient_id,
                }
                attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        return attachment_ids

    def send_mail(self, cr, uid, ids, context=None):
        mail_mail = self.pool.get('mail.mail')

        for wizard in self.browse(cr, uid, ids, context=context):
            values = self.generate_email(cr, uid, wizard, context=context)

            recipient_ids = []
            recipient_ids.append(values['customer_id'].id)
            email_to = values['customer_id'].name + ' <' + values['customer_id'].email + '>'
            values.pop('customer_id')

            json_string = wizard.json_object
            email_cc = ''
            if json_string:
                for json_data in json.loads(json_string):
                    email_cc = email_cc + json_data['email'] + ','
		
            if recipient_ids:
                warning = self.check_partners_email(cr, uid, recipient_ids, context=context)
                if warning:
                    message = warning['warning']['message']
                    raise osv.except_osv(_("Warning"), _(message))

                values['body_html'] = values['body']
                values['email_cc'] = email_cc
                values['email_recipients'] = email_to + ',' + email_cc[:-1]

                msg_id = mail_mail.create(cr, uid, values, context=context)
                mail = mail_mail.browse(cr, uid, msg_id, context=context)

                context.pop('default_type', None)
                ctx = dict(context)
                ctx.update({'bypass_cmis':True})

                attachment_ids = self.create_attachments(cr,uid,wizard,recipient_ids[0],mail.mail_message_id.id,context=ctx)

                if attachment_ids:
                    values['attachment_ids'] = [(6, 0, attachment_ids)]
                mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

                #send mail
                mail_mail.send(cr, uid, [msg_id], recipient_ids=recipient_ids, context=context)
                for recipient in self.pool.get('res.partner').browse(cr, uid, recipient_ids, context=context):
                    _logger.info('account.invoice mail %s: %s', values['subject'], recipient.email)

        return {'type': 'ir.actions.act_window_close'}

    def generate_email(self, cr, uid, wizard, context=None):
        values = {}
        for field in ['subject', 'body', 'customer_id', 'email_from', ]:
            values[field] = getattr(wizard, field)
        return values

    def attachment_name(self, report_name, extension):
        ext = "." + extension
        if not report_name.endswith(ext):
            report_name += ext
        return report_name

    def generate_report_attachment(self, cr, uid, reference, context=None):
        attachments = []
        ctx = dict(context)
        ctx.update({'bypass_create':True})
        res_id = context.get('default_res_id',False)
        model = context.get('default_model',False)
        service_name = context.get('service_name','account.invoice')
        ir_actions_report = self.pool.get('ir.actions.report.xml')
        report_ids = ir_actions_report.search(cr, uid, [('report_name','=',service_name)])
        for report in ir_actions_report.browse(cr, uid, report_ids, context=ctx):
            report_service = 'report.' + report.report_name
            service = netsvc.LocalService(report_service)
            result, res_format = service.create(cr, uid, [res_id], {'model': model}, context=ctx)
            result = base64.b64encode(result)
            report_name = self.attachment_name(reference if reference else report_service, res_format)
            attachments.append((report_name, result))
        return attachments

    def _get_view_id(self, cr, uid):
        """Get the view id
        @return: view id, or False if no view found
        """
        res = self.pool.get('ir.model.data').get_object_reference(cr, uid, 
                                                                  'natuurpunt_account_mail',
                                                                  'email_compose_message_wizard_np_account_form')
        return res and res[1] or False

    def get_wizard(self, cr, uid, context=None):
        res = { 'name': 'Verkoopfactuur via e-mail:',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice.mail.compose.message',
                'view_id': self._get_view_id(cr, uid),
                'target': 'new',
                'context': context, }
        return res

class account_invoice(osv.osv):

        _inherit = "account.invoice"

        def action_invoice_sent(self, cr, uid, ids, context=None):
            '''
            This function opens a window to compose an email, with the edi invoice template message loaded by default
            '''
            inv = self.browse(cr,uid,ids)[0]
            ir_model_data = self.pool.get('ir.model.data')
            try:
                if inv.journal_id.code == 'VO':
                    template_id = ir_model_data.get_object_reference(cr, uid, 'natuurpunt_account_mail', 'email_template_edi_vordering')[1]
                    service_name = 'account.vordering'
                elif inv.journal_id.code == 'VK':
                    template_id = ir_model_data.get_object_reference(cr, uid, 'natuurpunt_account_mail', 'email_template_edi_onkostennota')[1]
                    service_name = 'account.expense'
                else:
                    template_id = ir_model_data.get_object_reference(cr, uid, 'account', 'email_template_edi_invoice')[1]
                    service_name = 'account.invoice'
            except ValueError:
                template_id = False
            ctx = dict(context)
            ctx.update({
                'default_model': 'account.invoice',
                'default_res_id': ids[0],
                'default_use_template': bool(template_id),
                'default_template_id': template_id,
                'default_composition_mode': 'comment',
                'service_name': service_name,
            })
            return self.pool.get('account.invoice.mail.compose.message').get_wizard(cr, uid, context=ctx)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
