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

from openerp.osv import osv, fields
import re
import netsvc
from tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class payment_mode(osv.osv):
    _inherit= 'payment.mode'
    
    def _initiatingparty_default(self, cr, uid, field, context={}):
        _logger.warn('_initiatingparty_default, field=%s, context=%s', field, context)
        company = self.pool.get('res.users').browse(cr, uid, uid).company_id
        vat = company.partner_id.vat
        # Belgium, febelfin specs
        # To Do: add support for companies not subjected to VAT 
        if vat and vat[0:2].upper() == 'BE':
            kbo_nr = vat[2:].replace(' ','')
            if field == 'id':
                return kbo_nr
            else:
                return 'KBO-BCE'
        else:
            # complete for other countries
            return False
    
    def _initiatingparty_id_default(self, cr, uid, context={}):
        return self._initiatingparty_default(cr, uid, 'id', context=context)
        
    def _initiatingparty_issr_default(self, cr, uid, context={}):
        return self._initiatingparty_default(cr, uid, 'issr', context=context)
    
    _columns = {
        'type': fields.selection([
                ('manual', 'Manual'),
                ('iso20022', 'ISO 20022')], 
                'Type', select=1,
                help='Select the Payment Type for the Payment Mode.'), 
        'bank_id': fields.many2one('res.partner.bank', "Bank account",
            required=False, help='Bank Account for the Payment Mode'),
        'initgpty_id': fields.char('Initiating Party Id', size=35,
            help="Identifier of the Initiating Party."
                 "\nSpecify KBO-BCE number for Belgium."
                  "\n(Field: InitgPty.Id.OrgId.Othr.Id)"),  
         'initgpty_issr': fields.char('Initiating Party Id Issuer', size=35,
            help="Issuer of the Identifier of the Initiating Party."
                 "\nSpecify 'KBO-BCE' for Belgium."
                  "\n(Field: InitgPty.Id.OrgId.Othr.Issr)"),  
    }  
    _defaults = {
        'initgpty_id': _initiatingparty_id_default,   
        'initgpty_issr': _initiatingparty_issr_default,   
    }
    
    def _check_initiatingparty_id(self, cr, uid, ids, context=None):
        pm = self.browse(cr, uid, ids[0], context=context)
        if pm.initgpty_issr and not pm.initgpty_id:
            return False
        return True
    
    _constraints = [
        (_check_initiatingparty_id, "Configuration Error! Please complete the 'Initiating Party Id' field.", ['initgpty_id'])
    ]
payment_mode()

class payment_order(osv.osv):
    _inherit = 'payment.order'
       
    def get_wizard(self, type):
        if type == 'iso20022':
            return 'account_pain','action_account_pain_create'
        else:
            return super(payment_order, self).get_wizard(type)

    def action_open(self, cr, uid, ids, *args):
        for payment in self.browse(cr, uid, ids):
            for line in payment.line_ids:
                if line.amount_currency <= 0:
                    raise osv.except_osv(_('Payment Instruction Error!'),
                        _("Unsupported Payment Instruction in Payment Line %s.\n"   \
                          "The value '%s' is less than the minimum value allowed.")
                          % (line.name, line.amount_currency))
        return super(payment_order, self).action_open(cr, uid, ids, *args)

    def unlink(self, cr, uid, ids, context=None):
        for order in self.browse(cr, uid, ids, context=context):
            if order.state == 'done':
                raise osv.except_osv(_('Error'),
                    _("You can not remove a Payment Order that has already been processed !" \
                      "\nIf such an action is required, you should first cancel the Order."))
        return super(payment_order, self).unlink(cr, uid, ids, context=context)
    
    def button_undo_payment(self, cr, uid, ids, context=None):
        att_obj = self.pool.get('ir.attachment')
        for order in self.browse(cr, uid, ids, context=context):
            att_ids = att_obj.search(cr, uid, [('res_model', '=', 'payment.order'), ('res_id', '=', order.id)])
            if att_ids:
                att_obj.unlink(cr, uid, att_ids)
            self.write(cr, uid, order.id, {'state': 'draft'})
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_delete(uid, 'payment.order', order.id, cr)
            wf_service.trg_create(uid, 'payment.order', order.id, cr)
        return True

payment_order()

def check_bba_comm(val):
    supported_chars = '0-9+*/ '
    pattern = re.compile('[^' + supported_chars + ']')
    if pattern.findall(val or ''):
        return False                
    bbacomm = re.sub('\D', '', val or '')
    if len(bbacomm) == 12:
        base = int(bbacomm[:10])
        mod = base % 97 or 97      
        if mod == int(bbacomm[-2:]):
            return True
    return False

class payment_line(osv.osv):
    _inherit = 'payment.line'

    def _get_struct_comm_types(self, cr, uid, context=None):
        res = self.pool.get('account.invoice').fields_get(cr, uid, ['reference_type'], context)['reference_type']['selection']
        res.pop([i for i,x in enumerate(res) if x[0] == 'none'][0])
        bba_list = [i for i,x in enumerate(res) if x[0] == 'bba']
        if not bba_list:
            res.append(('bba', 'BBA Structured Communication'))
        return res

    def _check_communication(self, cr, uid, ids):
        for line in self.browse(cr, uid, ids):
            if line.state == 'structured':            
                if line.struct_comm_type == 'bba':
                    return check_bba_comm(line.communication)
        return True
    
    def fields_get(self, cr, uid, fields=None, context=None):
        fields = super(payment_line,self).fields_get(cr, uid, fields, context)
        if context is None:
            context = {}
        if context.get('payment_line_readonly'):
            for field in fields:
                fields[field]['readonly'] = True
        return fields

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('payment_line_readonly'):
            raise osv.except_osv(_('Warning'), _('Delete operation not allowed !' \
            '\nPlease go to the associated Payment Order in order to delete this payment line'))
        return super(payment_line, self).unlink(cr, uid, ids, context=context)
    
    def create(self, cr, uid, vals, context=None):     
        # copy structured communication of payment line is created by referencing an invoice
        if vals.has_key('move_line_id') and vals['move_line_id']:
            move_line = self.pool.get('account.move.line').browse(cr, uid, vals['move_line_id'], context)
            inv = move_line.invoice
            if inv and inv.reference_type != 'none':
                vals['state'] = 'structured' 
                vals['struct_comm_type'] = inv.reference_type
                vals['communication'] = inv.reference
        # verify correctness of bba structured communication when created via the payment line form
        if vals.has_key('state') and (vals['state'] == 'structured'):
            if vals.has_key('struct_comm_type') and (vals['struct_comm_type'] == 'bba'):               
                if vals.has_key('communication'):
                    bbacomm = vals['communication']
                    if check_bba_comm(bbacomm):
                        bbacomm = re.sub('\D', '', bbacomm)
                        vals['communication'] = '+++' + bbacomm[0:3] + '/' + bbacomm[3:7] + '/' + bbacomm[7:] + '+++'
                    else:
                        raise osv.except_osv(_('Payment Instruction Error!'), 
                            _('Invalid BBA Structured Communication in Payment Line %s , please correct !') % vals['name'])
        return super(payment_line, self).create(cr, uid, vals, context=context)       

    def write(self, cr, uid, ids, vals, context={}):
        if type(ids) is int:
            ids = [ids]    
        for line in self.browse(cr, uid, ids, context):
            vals2 = vals.copy()
            if vals.has_key('state'):
                line_state = vals['state']
            else:
                line_state = line.state
            if line_state == 'structured':
                if vals.has_key('struct_comm_type'):
                    struct_comm_type = vals['struct_comm_type']
                else:    
                    struct_comm_type = line.struct_comm_type or ''                            
                if struct_comm_type == 'bba':               
                    if vals.has_key('communication'):
                        bbacomm = vals['communication']
                    else:
                        bbacomm = line.communication or ''
                    if check_bba_comm(bbacomm):
                        bbacomm = re.sub('\D', '', bbacomm)
                        vals2['communication'] = '+++' + bbacomm[0:3] + '/' + bbacomm[3:7] + '/' + bbacomm[7:] + '+++'
                    else:
                        raise osv.except_osv(_('Payment Instruction Error!'), 
                            _('Invalid BBA Structured Communication in Payment Line %s , please correct !') % line.name)
            super(payment_line, self).write(cr, uid, [line.id], vals2, context)
        return True

    _columns = {
        'name': fields.char('Payment Line Ref.', size=64, required=True),
        'state': fields.selection([('normal','Free Communication'), ('structured','Structured Communication')], 'Communication Type', required=True),
        'struct_comm_type': fields.selection(_get_struct_comm_types, 'Structured Communication Type'),
    }
    _constraints = [
        (_check_communication, 'Invalid BBA Structured Communication !', ['Communication']),
        ]    
payment_line()
