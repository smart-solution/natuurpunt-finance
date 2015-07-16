# -*- encoding: utf-8 -*-

from mx import DateTime
import re, time, random
from openerp.tools.translate import _

from openerp.osv import fields, osv

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def create(self, cr, uid, vals, context=None):
#        if vals.has_key('internal_number'):
#            if not(vals['internal_number']):
#                vals.update({'reference': False,})
        res = super(account_invoice, self).create(cr, uid, vals, context=context)
        obj = self.browse(cr, uid, res)
        vals['type'] = obj.type
        if vals.has_key('type'):
            if vals['type'] == 'out_invoice':               
                partner_obj =  self.pool.get('res.partner').browse(cr, uid, vals['partner_id'])
                if not partner_obj.organisation_type_id:         
                    if partner_obj.out_inv_comm_type == None:
                        reference_type = 'bba'
                    else:
                           reference_type = partner_obj.out_inv_comm_type
                    algorithm = partner_obj.out_inv_comm_algorithm
                    if vals.has_key('reference'):
                        ref = vals['reference']
                    else:
                        ref = ''
                    reference = self.generate_bbacomm(cr, uid, obj.id, vals['type'], reference_type, vals['partner_id'], ref)
#                    reference = self.generate_bbacomm(cr, uid, obj.id, 'out_invoice', reference_type, algorithm, vals['partner_id'], '')
                    self.pool.get('account.invoice').write(cr, uid, [obj.id], {'reference':reference['value']['reference'], 'reference_type':reference_type, }, context=context)
        if not vals.has_key('type'):
                partner_obj =  self.pool.get('res.partner').browse(cr, uid, vals['partner_id'])
                if partner_obj.out_inv_comm_type == None:
                    reference_type = 'bba'
                else:
                       reference_type = partner_obj.out_inv_comm_type
                algorithm = partner_obj.out_inv_comm_algorithm
                reference = self.generate_bbacomm(cr, uid, obj.id, 'out_invoice', reference_type, vals['partner_id'], '')
#                reference = self.generate_bbacomm(cr, uid, obj.id, 'out_invoice', reference_type, algorithm, vals['partner_id'], '')
                self.pool.get('account.invoice').write(cr, uid, [obj.id], {'reference':reference['value']['reference'], 'reference_type':reference_type, }, context=context)
        return res

    def generate_bbacomm(self, cr, uid, ids, type, reference_type, partner_id, reference, context=None):
        partner_obj =  self.pool.get('res.partner')
        reference = reference or ''
        algorithm = False
        if partner_id:
            algorithm = partner_obj.browse(cr, uid, partner_id, context=context).out_inv_comm_algorithm
        algorithm = algorithm or 'random'
        if (type == 'out_invoice'):
            if reference_type == 'bba':
                if algorithm == 'date':
                    if not self.check_bbacomm(reference):
                        doy = time.strftime('%j')
                        year = time.strftime('%Y')
                        seq = '001'
                        seq_ids = self.search(cr, uid,
                            [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                             ('reference', 'like', '+++%s/%s/%%' % (doy, year))], order='reference desc', limit=1)
                        if seq_ids:
                            prev_seq = int(self.browse(cr, uid, seq_ids[-1]).reference[12:15])
                            if prev_seq < 999:
                                seq = '%03d' % (prev_seq + 1)
                            else:
                                raise osv.except_osv(_('Warning!'),
                                    _('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!' \
                                      '\nPlease create manually a unique BBA Structured Communication.'))
                        bbacomm = doy + year + seq
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        reference = '+++%s/%s/%s%02d+++' % (doy, year, seq, mod)
                elif algorithm == 'partner_ref':
                    if not self.check_bbacomm(reference):
#                        partner_ref = self.pool.get('res.partner').browse(cr, uid, partner_id).ref
                        partner_ref = str(partner_id)
                        partner_ref_nr = re.sub('\D', '', partner_ref or '')
                        if (len(partner_ref_nr) < 3) or (len(partner_ref_nr) > 7):
#                            raise osv.except_osv(_('Warning!'),
#                                _('The Partner should have a 3-7 digit Reference Number for the generation of BBA Structured Communications!' \
#                                  '\nPlease correct the Partner record.'))
                            partner_ref_nr = "%s%s" % ('99999', partner_ref_nr.ljust(2, '0'))
                        else:
                            partner_ref_nr = partner_ref_nr.ljust(7, '0')
                        prev_seq = 0
                        reference = 'yes'
                        while reference == 'yes' or self.check_bbacomm_exists(cr, uid, reference):
                            prev_seq += 1
                            if prev_seq < 999:
                                seq = '%03d' % (prev_seq)
                            else:
                                raise osv.except_osv(_('Warning!'),
                                    _('The daily maximum of outgoing invoices with an automatically generated BBA Structured Communications has been exceeded!' \
                                      '\nPlease create manually a unique BBA Structured Communication.'))
                            bbacomm = partner_ref_nr + seq
                            base = int(bbacomm)
                            mod = base % 97 or 97
                            reference = '+++%s/%s/%s%02d+++' % (partner_ref_nr[:3], partner_ref_nr[3:], seq, mod)
                elif algorithm == 'random':
                    if not self.check_bbacomm(reference):
                        base = random.randint(1, 9999999999)
                        bbacomm = str(base).rjust(10, '0')
                        base = int(bbacomm)
                        mod = base % 97 or 97
                        mod = str(mod).rjust(2, '0')
                        reference = '+++%s/%s/%s%s+++' % (bbacomm[:3], bbacomm[3:7], bbacomm[7:], mod)
                else:
                    raise osv.except_osv(_('Error!'),
                        _("Unsupported Structured Communication Type Algorithm '%s' !" \
                          "\nPlease contact your OpenERP support channel.") % algorithm)
        return {'value': {'reference': reference}}

    def check_bbacomm_exists(self, cr, uid, val):
        obj_mailing_partner = self.pool.get('mailing.list.partner')
        same_refs = obj_mailing_partner.search(cr, uid, [('reference', '=', val)])
        if same_refs:
            print 'dubbele bba in mailing: ', val
            return True
        obj_account_invoice = self.pool.get('account.invoice')
        same_inv_refs = obj_account_invoice.search(cr, uid, [('type', '=', 'out_invoice'), ('reference_type', '=', 'bba'),
                         ('reference', '=', val)])
        if same_inv_refs:
            print 'dubbele bba in invoice: ', val
            return True
        return False

account_invoice()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
