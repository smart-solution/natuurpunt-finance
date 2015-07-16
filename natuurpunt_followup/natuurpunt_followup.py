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
from openerp.tools.translate import _
import datetime
from datetime import timedelta
from datetime import date

#class account_followup_print(osv.osv_memory):
#    _inherit = 'account_followup.print'
#
#    _columns = {
#    }
#
#    def process_partners(self, cr, uid, partner_ids, data, context=None):
#        partner_obj = self.pool.get('res.partner')
#        partner_ids_to_print = []
#        nbmanuals = 0
#        manuals = {}
#        nbmails = 0
#        nbunknownmails = 0
#        nbprints = 0
#        resulttext = " "
#        for partner in self.pool.get('account_followup.stat.by.partner').browse(cr, uid, partner_ids, context=context):
#            print 'TO PROCESS:',partner.partner_id.name
#            if partner.partner_id.payment_next_action_date > date.today().strftime('%Y-%m-%d'):
#                print 'NOT TO BE PROCESSED'
#                continue
#            if partner.max_followup_id.manual_action:
#                partner_obj.do_partner_manual_action(cr, uid, [partner.partner_id.id], context=context)
#                nbmanuals = nbmanuals + 1
#                key = partner.partner_id.payment_responsible_id.name or _("Anybody")
#                if not key in manuals.keys():
#                    manuals[key]= 1
#                else:
#                    manuals[key] = manuals[key] + 1
#            if partner.max_followup_id.send_email:
#                nbunknownmails += partner_obj.do_partner_mail(cr, uid, [partner.partner_id.id], context=context)
#                nbmails += 1
#            if partner.max_followup_id.send_letter:
#                partner_ids_to_print.append(partner.id)
#                nbprints += 1
#                message = _("Follow-up letter of ") + "<I> " + partner.partner_id.latest_followup_level_id_without_lit.name + "</I>" + _(" will be sent")
#                partner_obj.message_post(cr, uid, [partner.partner_id.id], body=message, context=context)
#        if nbunknownmails == 0:
#            resulttext += str(nbmails) + _(" email(s) sent")
#        else:
#            resulttext += str(nbmails) + _(" email(s) should have been sent, but ") + str(nbunknownmails) + _(" had unknown email address(es)") + "\n <BR/> "
#        resulttext += "<BR/>" + str(nbprints) + _(" letter(s) in report") + " \n <BR/>" + str(nbmanuals) + _(" manual action(s) assigned:")
#        needprinting = False
#        if nbprints > 0:
#            needprinting = True
#        resulttext += "<p align=\"center\">"
#        for item in manuals:
#            resulttext = resulttext + "<li>" + item + ":" + str(manuals[item]) +  "\n </li>"
#        resulttext += "</p>"
#        result = {}
#        action = partner_obj.do_partner_print(cr, uid, partner_ids_to_print, data, context=context)
#        result['needprinting'] = needprinting
#        result['resulttext'] = resulttext
#        result['action'] = action or {}
#        return result
#
#account_followup_print()

class account_journal(osv.osv):
    _inherit = 'account.journal'

    _columns = {
        'auto_block_followup': fields.boolean('Block followup'),
    }

account_journal()

class account_move_line(osv.osv):
    _inherit = 'account.move.line'

    def create(self, cr, uid, vals, context=None):
        print 'VALS:',vals
        res = super(account_move_line, self).create(cr, uid, vals, context=context)
        line = self.browse(cr, uid, res)

        if line.journal_id:
            if line.journal_id.auto_block_followup:
                self.write(cr, uid, [res], {'blocked':True})

        return res

account_move_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
