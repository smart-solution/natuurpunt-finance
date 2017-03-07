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
from datetime import datetime
from tools.translate import _
from openerp.addons.connector.queue.job import job
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.exception import FailedJobError
from openerp import SUPERUSER_ID

# ATTENTION
# To start the server:
# ./openerp-server --database=natuurpunt --addons-path=addons --log-handler=openerp.addons.connector:DEBUG --load=web,web_kanban,connector --workers=0

@job
def job_confirm_bank_statement(session, ids, context):
    """
    Use connector for asynchronous processing of bank statements
    """

    try:
        BankStatement = session.pool.get('account.bank.statement')
        res = BankStatement.button_confirm_bank(session.cr, session.uid, ids, context=context)
	session.pool.get('account.bank.statement').write(session.cr, session.uid, ids, {'state':'confirm'})

        # Send the email to the user
        user = session.pool.get('res.users').browse(session.cr, session.uid, session.uid)
    
        data_obj = session.pool.get('ir.model.data')
        template = data_obj.get_object(session.cr, session.uid, 'account_bank_statement_async', 'bank_statetement_processed_template')
    
        context['subject']   = "Het rekeninguittreksel %s s verwerkt"%(ids)
        context['email_to']  = user.email
        context['body_html'] = "<p>Het rekeninguittreksel %s wordt verwerkt</p>"%(ids)
        mail_res = session.pool.get('account.bank.statement').send_processed_mail(session.cr, SUPERUSER_ID, template.id, ids[0], context=context)
    
    except ValueError, e:
	session.pool.get('account.bank.statement').write(session.cr, session.uid, ids, {'process_log':e, 'state':'error'})
    
    return res

class account_bank_statement(osv.osv):

    _inherit = 'account.bank.statement'

    def send_processed_mail(self, cr, uid, template_id, res_id, context=None):
	"""
	Generate an email for the async notification of bank statement processing
	"""
        if context is None:
            context = {}
        mail_mail = self.pool.get('mail.mail')
        ir_attachment = self.pool.get('ir.attachment')

        user = self.pool.get('res.users').browse(cr, uid, context['recipient'])
	stmt = self.pool.get('account.bank.statement').browse(cr, uid, res_id)

        values = {}
        values['subject']   = "Het rekeninguittreksel %s s verwerkt"%(stmt.name)
        values['email_to']  = user.email
        values['email_from']  = "no_reply@natuurpunt.be"
        values['body_html'] = "<p>Het rekeninguittreksel %s wordt verwerkt</p>"%(stmt.name)
	
        if not values.get('email_from'):
            raise osv.except_osv(_('Warning!'),_("Sender email is missing or empty after template rendering. Specify one to deliver your message"))
        recipient_ids = []
	recipient_ids.append(user.partner_id.id)

        msg_id = mail_mail.create(cr, uid, values, context=context)
        mail = mail_mail.browse(cr, uid, msg_id, context=context)

        mail_mail.send(cr, uid, [msg_id], recipient_ids=recipient_ids, context=context)

        return msg_id


    def test_send_email(self, cr, uid, ids, context=None):

        # Send the email to the user
        user = self.pool.get('res.users').browse(cr, uid, uid)
    
        data_obj = self.pool.get('ir.model.data')
        template = data_obj.get_object(cr, uid, 'account_bank_statement_async', 'bank_statetement_processed_template')
    
        context['subject']   = "Het rekeninguittreksel %s s verwerkt"%(ids)
        context['email_to']  = user.email
        context['body_html'] = "<p>Het rekeninguittreksel %s wordt verwerkt</p>"%(ids)
        mail_res = self.pool.get('email.template').send_mail(cr, SUPERUSER_ID, template.id, False, force_send=True, context=context)
	

    def button_confirm_bank_async(self, cr, uid, ids, context=None):
	"""
	Method to call the async processing of bank statement
	"""
        session = ConnectorSession(cr, uid, context)
	
	context['recipient'] = uid
	res = job_confirm_bank_statement.delay(session, ids, context)

	self.pool.get('account.bank.statement').write(cr, uid, ids, {'state':'processing'})
	
	return True

    def write(self, cr, uid, ids, vals, context=None):
	if 'validated' not in vals and 'state' not in vals:
	    vals['validated'] = False
        return super(account_bank_statement, self).write(cr, uid, ids, vals=vals, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
