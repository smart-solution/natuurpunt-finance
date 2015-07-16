#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
# 
##############################################################################
import base64
import datetime, time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools
from md5 import md5

import logging

_logger = logging.getLogger(__name__)

class account_coda_account(osv.osv):
    _name = 'account.coda.account'
    _description = 'Account Coda Communication'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True, select=True),
        'name': fields.char('Name', size=64, required=True, translate=True),
        'account_id': fields.many2one('account.account', 'Account', required=True, select=True),
        'communication_equal': fields.char('Structured Communication', size=32),
        'amount': fields.float('Amount'),
        'communication_like': fields.char('Part of Free Communication', size=32),
        'journal_id': fields.many2one('account.journal', 'Journal', required=True, select=True),
# 1 line added for NP transaction code improvement
        'transaction_code': fields.char('Transaction Code', size=8),
        'analytic_dimension_1_id': fields.many2one('account.analytic.account', 'Dimension 1'),
        'analytic_dimension_2_id': fields.many2one('account.analytic.account', 'Dimension 2'),
        'analytic_dimension_3_id': fields.many2one('account.analytic.account', 'Dimension 3'),
        'analytic_dimension_1_required': fields.boolean("Analytic Dimension 1 Required"),
        'analytic_dimension_2_required': fields.boolean("Analytic Dimension 2 Required"),
        'analytic_dimension_3_required': fields.boolean("Analytic Dimension 3 Required"),
     }

    _defaults = {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id
    }

account_coda_account()

class account_analytic_account(osv.osv):
    _inherit = 'account.analytic.account'
    
    _columns = {
        'old_code': fields.char("Oude Code"),
                }
account_analytic_account()

class account_bank_statement(osv.osv):
    _inherit = 'account.bank.statement'
    
    _columns = {
        'fys_file_id': fields.many2one('account.coda.fys.file', 'Fys. File', select=True),
        'det2_ids': fields.one2many('account.coda.det2', 'stat_id', 'Coda Detail Lines'),
        'det3_ids': fields.one2many('account.coda.det3', 'stat_id', 'Coda Detail Information'),
        'sdd_ref_ids': fields.one2many('account.coda.sdd.refused', 'stat_id', 'SDD Refused'),
               }
    
    def unlink(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context):
            if this.fys_file_id:
                this.fys_file_id.write(
                        {'filename': this.fys_file_id.id,
                        })
                this.fys_file_id.refresh()
        return super(account_bank_statement, self).unlink(
                cr, uid, ids, context=context)
    
account_bank_statement()
    
class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def create(self, cr, uid, vals, context=None):
        coda_id = 0
        
# New analytic code contract, fonds, project
        if 'name' in vals and vals['name']:
            sql_stat = "select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id,  account_analytic_account.id as analytic_dimension_3_id from account_coda_account, account_bank_statement, account_analytic_account where ('%s' like '%s' || account_analytic_account.code || '%s') and (account_analytic_account.code like 'P-%s' or account_analytic_account.code like 'C-%s' or account_analytic_account.code like 'F-%s') and account_coda_account.name = 'Giften-afleiding' and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_analytic_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['name'].replace("'", ""), '%', '%', '%', '%', '%', vals['account_id'], vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']
                vals['analytic_dimension_1_id'] = sql_res['analytic_dimension_1_id']
                vals['analytic_dimension_2_id'] = sql_res['analytic_dimension_2_id']
                vals['analytic_dimension_3_id'] = sql_res['analytic_dimension_3_id']

# Old analytic code
        if 'name' in vals and vals['name'] and 'structcomm_flag' in vals and not(vals['structcomm_flag']):
            sql_stat = "select account_coda_account.id as coda_id, account_id, account_analytic_dimension.sequence, account_analytic_account.id as analytic_account_id, default_dimension_1_id, default_dimension_2_id, default_dimension_3_id from account_coda_account, account_bank_statement, account_analytic_account, account_analytic_dimension where ('%s' like '%s ' || account_analytic_account.old_code || '%s') and not(account_analytic_account.old_code IS NULL) and not(account_analytic_account.old_code = '') and account_coda_account.name = 'Giften-afleiding' and account_analytic_account.dimension_id = account_analytic_dimension.id and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_analytic_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['name'].replace("'", ""), '%', '%', vals['account_id'], vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']
                if sql_res['sequence'] == 1:
                    vals['analytic_dimension_1_id'] = sql_res['analytic_account_id']
                    vals['analytic_dimension_2_id'] = sql_res['default_dimension_2_id']
                    vals['analytic_dimension_3_id'] = sql_res['default_dimension_3_id']
                if sql_res['sequence'] == 2:
                    vals['analytic_dimension_2_id'] = sql_res['analytic_account_id']
                    vals['analytic_dimension_1_id'] = sql_res['default_dimension_1_id']
                    vals['analytic_dimension_3_id'] = sql_res['default_dimension_3_id']
                if sql_res['sequence'] == 3:
                    vals['analytic_dimension_3_id'] = sql_res['analytic_account_id']
                    vals['analytic_dimension_2_id'] = sql_res['default_dimension_2_id']
                    vals['analytic_dimension_1_id'] = sql_res['default_dimension_1_id']

# Description
        if 'name' in vals and vals['name']:
            sql_stat = "select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id from account_coda_account, account_bank_statement where ('%s' like '%s' || communication_like || '%s') and not(communication_like IS NULL) and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['name'].replace("'", ""), '%', '%', vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']

# Amount
        sql_stat = 'select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id  from account_coda_account, account_bank_statement where amount <> 0 and amount = %f and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id' % (vals['amount'], vals['account_id'], vals['statement_id'], )
        cr.execute(sql_stat)
        for sql_res in cr.dictfetchall():
            vals['account_id'] = sql_res['account_id']
            vals['analytic_dimension_1_id'] = sql_res['analytic_dimension_1_id']
            vals['analytic_dimension_2_id'] = sql_res['analytic_dimension_2_id']
            vals['analytic_dimension_3_id'] = sql_res['analytic_dimension_3_id']

# Description
        if 'name' in vals and vals['name']:
            sql_stat = "select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id  from account_coda_account, account_bank_statement where ('%s' like '%s' || communication_like || '%s') and not(communication_like IS NULL) and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['name'].replace("'", ""), '%', '%', vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']
                vals['analytic_dimension_1_id'] = sql_res['analytic_dimension_1_id']
                vals['analytic_dimension_2_id'] = sql_res['analytic_dimension_2_id']
                vals['analytic_dimension_3_id'] = sql_res['analytic_dimension_3_id']

# Transaction code
        if 'transaction_code' in vals and vals['transaction_code'] and vals['transaction_code'] != '':
            sql_stat = "select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id  from account_coda_account, account_bank_statement where transaction_code = '%s' and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['transaction_code'], vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']
                vals['analytic_dimension_1_id'] = sql_res['analytic_dimension_1_id']
                vals['analytic_dimension_2_id'] = sql_res['analytic_dimension_2_id']
                vals['analytic_dimension_3_id'] = sql_res['analytic_dimension_3_id']

        res = super(account_bank_statement_line, self).create(cr, uid, vals, context=context)
        return res

    _columns = {
# 1 line added for NP transaction code improvement
        'transaction_code': fields.char('Trans.Code', size=8),
        'structcomm_flag': fields.boolean('OGM Gebruikt'),
        'structcomm_message': fields.char('OGM Bericht'),
        'lines2_id': fields.many2one('account.coda.lines2', 'Coda Lines', select=True),
        'det2_ids': fields.one2many('account.coda.det2', 'stat_line_id', 'Coda Detail Lines'),
        'det3_ids': fields.one2many('account.coda.det3', 'stat_line_id', 'Coda Detail Details'),
                }

account_bank_statement_line()

class account_coda_fys_file(osv.osv):
    _name = 'account.coda.fys.file'
    _description = 'Coda Fysical File'

    _columns = {
        'filename': fields.char('Name', size=128),
        'files_ids': fields.one2many('account.coda.file', 'fys_file_id', 'Coda Files', ondelete='cascade'),
                }

account_coda_fys_file()

class account_coda_file(osv.osv):
    _name = 'account.coda.file'
    _description = 'Coda File'

    _columns = {
        'fys_file_id': fields.many2one('account.coda.fys.file', 'Fys. File', select=True),
        't0_date': fields.date('Date'),
        't0_bankid': fields.integer('Bank Id Nbr'),
        't0_app_code': fields.integer('Application Code'),
        't0_dup': fields.char('Duplicate', size=1),
        't0_file_ref': fields.char('File Reference', size=10),
        't0_addressed_to': fields.char('Addressed to', size=26),
        't0_BIC': fields.char('BIC', size=11),
        't0_comp_id': fields.char('Account Owner', size=11),
        't0_sep_appl': fields.char('Seperate Application', size=5),
        't0_trans_ref': fields.char('Transaction Ref.', size=16),
        't0_rel_ref': fields.char('Related Ref.', size=16),
        't0_version': fields.char('Version', size=1),
        't1_struct': fields.integer('Account Struct.'),
        't1_paper_seq_nbr': fields.char('Paper Seq. Nbr.', size=3),
        't1_account_nbr': fields.char('Account', size=34),
        't1_currency': fields.char('Currency', size=3),
        't1_start_balance': fields.float('Start Balance'),
        't1_start_date': fields.date('Start Date'),
        't1_account_holder': fields.char('Account Holder', size=26),
        't1_account_descr': fields.char('Account Description', size=35),
        't1_seq_nbr': fields.char('File Seq Nbr.', size=3),
        't8_paper_seq_nbr': fields.char('Paper Seq. Nbr.', size=3),
        't8_account_nbr': fields.char('Account', size=34),
        't8_currency': fields.char('Currency', size=3),
        't8_end_balance': fields.float('Start Balance'),
        't8_end_date': fields.date('Start Date'),
        't9_nbr_lines': fields.integer('Number of lines'),
        't9_debet': fields.float('Total Debet'),
        't9_credit': fields.float('Total Credit'),
        'lines2_ids': fields.one2many('account.coda.lines2', 'file_id', 'Files', ondelete='cascade'),
        'free_message_ids': fields.one2many('account.coda.free.message', 'file_id', 'Free Message', ondelete='cascade'),
                }

account_coda_file()

class account_coda_free_message(osv.osv):
    _name = 'account.coda.free.message'
    _description = 'Coda Free Message'

    _columns = {
        'file_id': fields.many2one('account.coda.file', 'File', select=True),
        'det_nbr': fields.char('Detail Nbr.', size=4),
        'free_message': fields.char('Free message', size=80)
                }

account_coda_free_message()

class account_coda_lines2(osv.osv):
    _name = 'account.coda.lines2'
    _description = 'Coda lines'
    
    _columns = {
        'file_id': fields.many2one('account.coda.file', 'Coda File', select=True),
        't21_seq_nbr': fields.char('File Seq Nbr.', size=4),
        't21_det_nbr': fields.char('Detail Nbr.', size=4),
        't21_bank_ref': fields.char('Bank reference', size=21),
        't21_amount': fields.float('Amount'),
        't21_date': fields.date('Val. Date'),
        't21_code': fields.char('Code', size=8),
        't21_struct': fields.boolean('Structured'),
        't21_struct_type': fields.char('Struct. Type', size=3),
        't21_struct_comm': fields.char('Struct. Comm.', size=50),
        't21_free_comm': fields.char('Communication', size=53),
        't21_date_booking': fields.date('Date booking'),
        't21_paper_seq_nbr': fields.char('Paper Seq. Nbr.', size=3),
        't21_glob': fields.integer('Glob. Code'),
        't22_free_comm': fields.char('Communication', size=53),
        't22_ref_cust': fields.char('Ref. Cust', size=35),
        't22_BIC': fields.char('BIC', size=11),
        't22_purpose_cat': fields.char('Purpose Cat.', size=4),
        't22_purpose': fields.char('Purpose', size=4),
        't23_account_nbr': fields.char('Account', size=34),
        't23_currency': fields.char('Currency', size=3),
        't23_partner': fields.char('Name', size=35),
        't23_free_comm': fields.char('Communication', size=43),
        'lines3_ids': fields.one2many('account.coda.lines3', 'lines2_id', 'Line Items', ondelete='cascade'),
        'det2_ids': fields.one2many('account.coda.det2', 'lines2_id', 'Line Details', ondelete='cascade'),
                }
    
account_coda_lines2()

class account_coda_lines3(osv.osv):
    _name = 'account.coda.lines3'
    _description = 'Coda Line Items'
    
    _columns = {
        'lines2_id': fields.many2one('account.coda.lines2', 'Coda Lines', select=True),
        't31_det_nbr': fields.char('Detail Nbr.', size=4),
        't31_code': fields.char('Operation Code', size=8),
        't31_struct': fields.boolean('Structured'),
        't31_struct_type': fields.char('Struct. Type', size=3),
        't31_struct_comm': fields.char('Struct. Comm.', size=70),
        't31_free_comm': fields.char('Communication', size=73),
        't32_free_comm': fields.char('Communication', size=105),
        't33_free_comm': fields.char('Communication', size=90),
                }
    
account_coda_lines3()

class account_coda_det2(osv.osv):
    _name = 'account.coda.det2'
    _description = 'Coda Detail lines'
    
    _columns = {
        'lines2_id': fields.many2one('account.coda.lines2', 'Item line', select=True),
        'stat_id': fields.many2one('account.bank.statement', 'Bank Statement'),
        'stat_line_id': fields.many2one('account.bank.statement.line', 'Item line'),
        't21_seq_nbr': fields.char('File Seq Nbr.', size=4),
        't21_det_nbr': fields.char('Detail Nbr.', size=4),
        't21_bank_ref': fields.char('Bank reference', size=21),
        't21_amount': fields.float('Amount'),
        't21_date': fields.date('Val. Date'),
        't21_code': fields.char('Code', size=8),
        't21_struct': fields.boolean('Structured'),
        't21_struct_type': fields.char('Struct. Type', size=3),
        't21_struct_comm': fields.char('Struct. Comm.', size=50),
        't21_free_comm': fields.char('Communication', size=53),
        't21_date_booking': fields.date('Date booking'),
        't21_paper_seq_nbr': fields.char('Paper Seq. Nbr.', size=3),
        't21_glob': fields.integer('Glob. Code'),
        't22_free_comm': fields.char('Communication', size=53),
        't22_ref_cust': fields.char('Ref. Cust', size=35),
        't22_BIC': fields.char('BIC', size=11),
        't22_purpose_cat': fields.char('Purpose Cat.', size=4),
        't22_purpose': fields.char('Purpose', size=4),
        't23_account_nbr': fields.char('Account', size=34),
        't23_currency': fields.char('Currency', size=3),
        't23_partner': fields.char('Name', size=35),
        't23_free_comm': fields.char('Communication', size=43),
        'det3_ids': fields.one2many('account.coda.det3', 'det2_id', 'Item Informations', ondelete='cascade'),
                }
    
account_coda_det2()

class account_coda_det3(osv.osv):
    _name = 'account.coda.det3'
    _description = 'Coda Detail Items'
    
    _columns = {
        'det2_id': fields.many2one('account.coda.det2', 'Detail Line', select=True),
        'stat_id': fields.many2one('account.bank.statement', 'Bank Statement'),
        'stat_line_id': fields.many2one('account.bank.statement.line', 'Item line'),
        't31_seq_nbr': fields.char('Detail Seq Nbr.', size=4),
        't31_det_nbr': fields.char('Detail Nbr.', size=4),
        't31_code': fields.char('Operation Code', size=8),
        't31_struct': fields.boolean('Structured'),
        't31_struct_type': fields.char('Struct. Type', size=3),
        't31_struct_comm': fields.char('Struct. Comm.', size=70),
        't31_free_comm': fields.char('Communication', size=73),
        't32_free_comm': fields.char('Communication', size=105),
        't33_free_comm': fields.char('Communication', size=90),
                }
    
account_coda_det3()

class account_coda_sdd_refused(osv.osv):
    _name = 'account.coda.sdd.refused'
    _description = 'Coda SDD refused lines'
    
    _columns = {
        'lines2_id': fields.many2one('account.coda.lines2', 'Item line', select=True),
        'stat_id': fields.many2one('account.bank.statement', 'Bank Statement'),
        'date': fields.date('Settlement Date'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True),
#         'sdd_mandate_id': fields.many2one('sdd.mandate', 'Mandate', select=True),
        'type': fields.char('Type', size=1),
        'scheme': fields.char('Scheme', size=1),
        'pay_reason': fields.char('Paid or reason', size=1),
        'partner': fields.char('Partner', size=35),
        'mandate_ref': fields.char('Reference', size=35),
        'comm': fields.char('Reference', size=62),
        'type_R': fields.char('Type R', size=1),
        'reason': fields.char('Reason', size=1),
                }

account_coda_sdd_refused()

class account_coda_import(osv.osv_memory):
    _inherit = 'account.coda.import'

    def _get_default_tmp_account(self, cr, uid, context):
        user = self.pool.get('res.users').browse(cr, uid, uid) 
        tmp_accounts = self.pool.get('account.account').search(cr, uid, [('code', '=', '499010'),('company_id','=',user.company_id.id)])
        if tmp_accounts and len(tmp_accounts) > 0:
            tmp_account_id = tmp_accounts[0]
        else:
            tmp_account_id = False
        return tmp_account_id
    
    def coda_parsing(self, cr, uid, ids, context=None, batch=False, codafile=None, codafilename=None):
        if context is None:
            context = {}
        if batch:
            codafile = str(codafile)
            codafilename = codafilename
        else:
            data = self.browse(cr, uid, ids)[0]
#             print 'data: ', data
            try:
                codafile = data.coda_data
                codafilename = data.coda_fname
                temporaryaccount = data.temporary_account_id.id
            except:
                raise osv.except_osv(_('Error'), _('Wizard in incorrect state. Please hit the Cancel button'))
                return {}
        recordlist = unicode(base64.decodestring(codafile), 'windows-1252', 'strict').split('\n')
        
        journal_obj = self.pool.get('account.journal')
        stat_obj = self.pool.get('account.bank.statement')
        stat_line_obj = self.pool.get('account.bank.statement.line')
        fys_file_obj = self.pool.get('account.coda.fys.file')
        file_obj = self.pool.get('account.coda.file')
        free_message_obj = self.pool.get('account.coda.free.message')
        lines2_obj = self.pool.get('account.coda.lines2')
        lines3_obj = self.pool.get('account.coda.lines3')
        det2_obj = self.pool.get('account.coda.det2')
        det3_obj = self.pool.get('account.coda.det3')
        partner_obj = self.pool.get('res.partner.bank')
        pay_line_obj = self.pool.get('payment.line')
        move_line_obj = self.pool.get('account.move.line')
        invoice_obj = self.pool.get('account.invoice')
        sdd_ref_obj = self.pool.get('account.coda.sdd.refused')
#         sdd_mandate_obj = self.pool.get('sdd.mandate')
 
        data_md5 = md5(codafile).digest()       
        exists = fys_file_obj.search(cr, uid, [('filename','=',data_md5)], context=context)
        if exists:
            raise osv.except_osv(_('Error'),_('Error') + _('Duplicate Coda filename'))
        fys_file_id = fys_file_obj.create(cr, uid, {'filename': data_md5}, context=context)
        
        prev = 9
        expect = 0
        counter = 0
        for line in recordlist:
#             print line
            counter += 1
            if not line:
                continue
            if line[0] == '0':
                # new Bank Statement = new file_obj
                if prev != 9:
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                if line[127] != '2':
                    raise osv.except_osv(_('Error'),_('Error: Incorrect CODA version %s') % line[127])
                file_id = file_obj.create(cr, uid, {
                      'fys_file_id': fys_file_id,
                      't0_date': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[5:11]), '%d%m%y')),
                      't0_bankid': line[11:14],
                      't0_app_code': line[14:16],
                      't0_dup': line[16],
                      't0_file_ref': line[24:34],
                      't0_addressed_to': line[34:60],
                      't0_BIC': rmspaces(line[60:71]),
                      't0_comp_id': line[71:82],
                      't0_sep_appl': rmspaces(line[83:88]),
                      't0_trans_ref': rmspaces(line[88:104]),
                      't0_rel_ref': rmspaces(line[104:120]),
                      't0_version': line[127],
                      }, context=context)
                prev = 0
                continue
            if line[0] == '1':
                if prev != 0:
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                balance = float(rmspaces(line[43:58])) / 1000
                if line[42] == '1':
                    balance = balance * -1
                if line[1] == '0':
                    account = rmspaces(line[5:17])
                    currency = rmspaces(line[18:21])                    
                elif line[1] == '1':
                    account = rmspaces(line[5:39])
                    currency = rmspaces(line[39:42])                    
                elif line[1] == '2':
                    account = rmspaces(line[5:39])
                    currency = rmspaces(line[39:42])                                        
                elif line[1] == '3':
                    account = rmspaces(line[5:39])
                    currency = rmspaces(line[39:42])                                        
                else:
                    raise osv.except_osv(_('Error: Incorrect account type at line %s') % str(counter))
                file = file_obj.search(cr, uid, [('id','=',file_id)])
                file_obj.write(cr, uid, file[0], {
                    't1_struct': line[1],
                    't1_paper_seq_nbr': line[2:5],
                    't1_account_nbr': account,
                    't1_currency': currency,
                    't1_start_balance': balance,
                    't1_start_date': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[58:64]), '%d%m%y')),
                    't1_account_holder': line[64:90],
                    't1_account_descr': line[90:125],
                    't1_seq_nbr': line[125:128],
                    }, context=context)
                prev = 1
                expect = 2
                continue
            if line[0] == '2':
                if line[1] == '1':
                    if line[6:10] == '0000':
                        if expect != 2:
                            raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                        amount = float(rmspaces(line[32:47])) / 1000
                        if line[31] == '1':
                            amount = amount * -1
                        struct = False
                        struct_type = ''
                        struct_comm = ''
                        free_comm = ''
                        if line[61] == '1':
                            struct = True
                            struct_type = line[62:65]
                            struct_comm = line[65:115]
                        else:
                            free_comm = rmspaces(line[62:115])
                        lines2_id = lines2_obj.create(cr, uid, {
                            'file_id': file_id,
                            't21_seq_nbr': line[2:6],
                            't21_det_nbr': line[6:10],
                            't21_bank_ref': line[10:31],
                            't21_amount': amount,
                            't21_date': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y')),
                            't21_code': line[54:62],
                            't21_struct': struct,
                            't21_struct_type': struct_type,
                            't21_struct_comm': struct_comm,
                            't21_free_comm': free_comm,
                            't21_date_booking': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[115:121]), '%d%m%y')),
                            't21_paper_seq_nbr': line[121:124],
                            't21_glob': int(rmspaces(line[124])),
                            }, context=context)
                        prev = 21
                        if line[125] == '1':
                            expect = 2
                        else:
                            if line[127] == '1':
                                expect = 31
                        continue
                    amount = float(rmspaces(line[32:47])) / 1000
                    if line[31] == '1':
                        amount = amount * -1
                    struct = False
                    struct_type = ''
                    struct_comm = ''
                    free_comm = ''
                    if line[61] == '1':
                        struct = True
                        struct_type = line[62:65]
                        struct_comm = line[65:115]
                    else:
                        free_comm = rmspaces(line[62:115])
                    det2_id = det2_obj.create(cr, uid, {
                        'lines2_id': lines2_id,
                        't21_seq_nbr': line[2:6],
                        't21_det_nbr': line[6:10],
                        't21_bank_ref': line[10:31],
                        't21_amount': amount,
                        't21_date': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y')),
                        't21_code': line[54:62],
                        't21_struct': struct,
                        't21_struct_type': struct_type,
                        't21_struct_comm': struct_comm,
                        't21_free_comm': free_comm,
                        't21_date_booking': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[115:121]), '%d%m%y')),
                        't21_paper_seq_nbr': line[121:124],
                        't21_glob': int(rmspaces(line[124])),
                        }, context=context)
                    prev = 121
                    if line[125] == '1':
                        expect = 2
                    else:
                        if line[127] == '1':
                            expect = 131
                    continue
                if line[1] == '2':
                    if line[6:10] == '0000':
                        if prev != 21:
                            raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                        lines2 = lines2_obj.search(cr, uid, [('id','=', lines2_id)])
                        lines2_obj.write(cr, uid, lines2[0], {
                            't22_free_comm': line[10:63],
                            't22_ref_cust': rmspaces(line[63:98]),
                            't22_BIC': rmspaces(line[98:109]),
                            't22_purpose_cat': line[117:121],
                            't22_purpose': line[121:125],
                            }, context=context)
                        prev = 21
                        if line[125] == '1':
                            expect = 2
                        else:
                            if line[127] == '1':
                                expect = 31
                        continue
                    if prev != 121:
                        raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                    det2 = det2_obj.search(cr, uid, [('id','=', det2_id)])
                    det2_obj.write(cr, uid, det2[0], {
                        't22_free_comm': line[10:63],
                        't22_ref_cust': rmspaces(line[63:98]),
                        't22_BIC': rmspaces(line[98:109]),
                        't22_purpose_cat': line[117:121],
                        't22_purpose': line[121:125],
                        }, context=context)
                    prev = 121
                    if line[125] == '1':
                        expect = 2
                    else:
                        if line[127] == '1':
                            expect = 131
                    continue
                if line[1] == '3':
                    if line[6:10] == '0000':
                        if prev != 21:
                            raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                        if line[22] == ' ':
                            account = rmspaces(line[10:22])
                            currency = rmspaces(line[23:26])
                        else:
                            account = rmspaces(line[10:44])
                            currency = rmspaces(line[44:47])
                        lines2 = lines2_obj.search(cr, uid, [('id', '=', lines2_id)])
                        lines2_obj.write(cr, uid, lines2[0], {
                            't23_account_nbr': account,
                            't23_currency': currency,
                            't23_partner': rmspaces(line[47:82]),
                            't23_free_comm': line[82:125],
                            }, context=context)
                        prev = 21
                        if line[127] == '1':
                            expect = 31
                        continue
                    if prev != 121:
                        raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                    if line[22] == ' ':
                        account = rmspaces(line[10:22])
                        currency = rmspaces(line[23:26])
                    else:
                        account = rmspaces(line[10:44])
                        currency = rmspaces(line[44:47])
                    det2 = det2_obj.search(cr, uid, [('id', '=', det2_id)])
                    det2_obj.write(cr, uid, det2[0], {
                        't23_account_nbr': account,
                        't23_currency': currency,
                        't23_partner': rmspaces(line[47:82]),
                        't23_free_comm': line[82:125],
                        }, context=context)
                    prev = 121
                    if line[127] == '1':
                        expect = 131
                    continue
                raise osv.except_osv(_('Error: Incorrect type at line %s') % str(counter))        
         
            
            if line[0] == '3':
                if line[1] == '1':
                    if expect == 31:
                        struct = False
                        struct_type = ''
                        struct_comm = ''
                        free_comm = ''
                        if line[39] == '1':
                            struct = True
                            struct_type = line[40:43]
                            struct_comm = line[43:113]
                        else:
                            free_comm = rmspaces(line[40:113])
                        lines3_id = lines3_obj.create(cr, uid, {
                            'lines2_id': lines2_id,
                            't31_seq_nbr': line[2:6],
                            't31_det_nbr': line[6:10],
                            't31_code': line[31:39],
                            't31_struct': struct,
                            't31_struct_type': struct_type,
                            't31_struct_comm': struct_comm,
                            't31_free_comm': free_comm,
                                                }, context=context)
                        prev = 31
                        expect = 2
                        if line[125] == '1':
                            expect = 32
                        if line[127] == '1':
                            expect = 31
                        continue
                    if expect == 131:
                        struct = False
                        struct_type = ''
                        struct_comm = ''
                        free_comm = ''
                        if line[39] == '1':
                            struct = True
                            struct_type = line[40:43]
                            struct_comm = line[43:113]
                        else:
                            free_comm = rmspaces(line[40:113])
                        det3_id = det3_obj.create(cr, uid, {
                            'det2_id': det2_id,
                            't31_seq_nbr': line[2:6],
                            't31_det_nbr': line[6:10],
                            't31_code': line[31:39],
                            't31_struct': struct,
                            't31_struct_type': struct_type,
                            't31_struct_comm': struct_comm,
                            't31_free_comm': free_comm,
                            }, context=context)
                        prev = 131
                        expect = 2
                        if line[125] == '1':
                            expect = 132
                        if line[127] == '1':
                            expect = 131
                        continue
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                if line[1] == '2':
                    if prev == 31:
                        lines3 = lines3_obj.search(cr, uid, [('id','=', lines3_id)])
                        lines3_obj.write(cr, uid, lines3[0], {
                            't32_free_comm': line[10:115],
                            }, context=context)
                        prev = 32
                        expect = 2
                        if line[125] == '1':
                            expect = 33
                        if line[127] == '1':
                            expect = 31
                        continue
                    # det_nbr <> '0000' dus een det-record updaten    
                    if prev == 131:
                        det3 = det3_obj.search(cr, uid, [('id','=', det3_id)])
                        det3_obj.write(cr, uid, det3[0], {
                            't32_free_comm': line[10:115],
                            }, context=context)
                        prev = 132
                        expect = 2
                        if line[125] == '1':
                            expect = 133
                        if line[127] == '1':
                            expect = 131
                        continue
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                if line[1] == '3':
                    if prev == 32:
                        lines3 = lines3_obj.search(cr, uid, [('id', '=', lines3_id)])
                        lines3_obj.write(cr, uid, lines3[0], {
                            't32_free_comm': line[10:100],
                            }, context=context)
                        prev = 33
                        expect = 2
                        if line[127] == '1':
                            expect = 31
                        continue
                    # det_nbr <> '0000' dus een det-record updaten    
                    if prev == 132:
                        det3 = det3_obj.search(cr, uid, [('id', '=', det3_id)])
                        det3_obj.write(cr, uid, det3[0], {
                            't32_free_comm': line[10:100],
                            }, context=context)
                        prev = 133
                        expect = 2
                        if line[127] == '1':
                            expect = 131
                        continue
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                raise osv.except_osv(_('Error: Incorrect type at line %s') % str(counter))        

            if line[0] == '8':
                if line[16] == ' ':
                    account = rmspaces(line[4:16])
                    currency = rmspaces(line[17:20])
                else:
                    account = rmspaces(line[4:38])
                    currency = rmspaces(line[38:41])
                balance = float(rmspaces(line[42:57])) / 1000
                if line[41] == '1':
                    balance = balance * -1
                file = file_obj.search(cr, uid, [('id','=',file_id)])
                file_obj.write(cr, uid, file[0], {
                    't8_paper_seq_nbr': line[1:3],
                    't8_account_nbr': account,
                    't8_currency': currency,
                    't8_end_balance': balance,
                    't8_end_date': time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[57:63]), '%d%m%y')),
                    }, context=context)
                prev = 8
                continue

            if line[0] == '4':
                if prev != 8:
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                free_id = free_message_obj.create(cr, uid, {
                    'file_id': file_id,
                    'det_nbr': line[6:10],
                    'free_message': line[32:112],
                    }, context=context)
                prev = 8
                continue
            
            if line[0] == '9':
                if prev != 8:
                    raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))
                file = file_obj.search(cr, uid, [('id','=',file_id)])
                file_obj.write(cr, uid, file[0], {
                    't9_nbr_lines': int(rmspaces(line[16:22])),
                    't9_debet': float(rmspaces(line[22:37])) / 1000,
                    't9_credit': float(rmspaces(line[37:52])) / 1000,
                    }, context=context)
                prev = 9
                expect = 999
                if line[127] == '1':
                    expect = 0
                continue
            raise osv.except_osv(_('Error'), _('Error: Incorrect type at line %s') %(str(counter)))

        fys_file = fys_file_obj.browse(cr, uid, fys_file_id)
        
        for cfile in fys_file.files_ids:
#             print 'journaal zoeken met: ', cfile.t1_account_nbr, ' ', cfile.t1_currency
#                 # Belgian Account Numbers are composed of 12 digits.
#                 # In OpenERP, the user can fill the bank number in any format: With or without IBan code, with or without spaces, with or without '-'
#                 # The two following sql requests handle those cases.
            if len(cfile.t1_account_nbr) >= 12:
#                     # If the Account Number is >= 12 digits, it is mostlikely a Belgian Account Number (With or without IBAN).
#                     # The following request try to find the Account Number using a 'like' operator.
#                     # So, if the Account Number is stored with IBAN code, it can be found thanks to this.
                cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') like %s", ('%' + cfile.t1_account_nbr + '%',))
            else:
#                     # This case is necessary to avoid cases like the Account Number in the CODA file is set to a single or few digits,
#                     # and so a 'like' operator would return the first account number in the database which matches.
                cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (cfile.t1_account_nbr,))
            bank_ids = [id[0] for id in cr.fetchall()]
#                 # Filter bank accounts which are not allowed
            bank_ids = partner_obj.search(cr, uid, [('id', 'in', bank_ids)])
            journal_id = None
            bank_account = None
            if bank_ids and len(bank_ids) > 0:
                bank_accs = partner_obj.browse(cr, uid, bank_ids)
                for bank_acc in bank_accs:
                    if bank_acc.journal_id.id and ((bank_acc.journal_id.currency.id and bank_acc.journal_id.currency.name == cfile.t1_currency) or (not bank_acc.journal_id.currency.id and bank_acc.journal_id.company_id.currency_id.name == cfile.t1_currency)):
                        journal_id = bank_acc.journal_id.id
                        bank_account = bank_acc
                        break
            if not bank_account:
                raise osv.except_osv(_('Error') + ' R1004', _("No matching Bank Account (with Account Journal) found.\n\nPlease set-up a Bank Account with as Account Number '%s' and as Currency '%s' and an Account Journal.") % (cfile.t1_account_nbr, cfile.t1_currency))
            
            journal = journal_obj.browse(cr, uid, journal_id)
            if cfile.t8_end_date:
                period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', journal.company_id.id), ('date_start', '<=', cfile.t8_end_date), ('date_stop', '>=', cfile.t8_end_date)])
            else:
                period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', journal.company_id.id), ('date_start', '<=', cfile.t0_date), ('date_stop', '>=', cfile.t0_date)])
            if not period_id:
                raise osv.except_osv(_('Error') + 'R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s for the company %s.") % (cfile.t8_end_date, journal.company_id.name))

            statName = cfile.t0_date[2:4] + '-' + cfile.t1_account_nbr[4:5] + cfile.t1_account_nbr[14:16] + '-' + cfile.t1_paper_seq_nbr
            print statName
            coda_note = ''

            balance_start_check_date = cfile.t0_date
            cr.execute('SELECT balance_end_real \
                FROM account_bank_statement \
                WHERE journal_id = %s and date <= %s \
                ORDER BY date DESC,id DESC LIMIT 1', (journal_id, balance_start_check_date))
            res = cr.fetchone()
            balance_start_check = res and res[0]
            if balance_start_check == None:
                if journal.default_debit_account_id and (journal.default_credit_account_id == journal.default_debit_account_id):
                    balance_start_check = journal.default_debit_account_id.balance
                else:
                    raise osv.except_osv(_('Error'), _("Configuration Error in journal %s!\nPlease verify the Default Debit and Credit Account settings.") % journal.name)
            if balance_start_check != cfile.t1_start_balance:
                coda_note = _("The CODA Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!") % (cfile.t1_account_descr + ' #' + statName, cfile.t1_start_balance, balance_start_check, journal.name)

            ids = stat_obj.search(cr, uid, [('name', '=', statName)])
            if ids:
                raise osv.except_osv(_('Error'), _('CODA messsage already imported!'))

            stat_id = stat_obj.create(cr, uid, {
                'balance_start': cfile.t1_start_balance,
                'journal_id': journal_id,
                'period_id': period_id[0],
#                 'total_entry_encoding': ,
                'date': cfile.t0_date,
                'user_id': uid,
                'name': statName,
                'closing_date': cfile.t8_end_date,
#                 'balance_end': ,
                'company_id': journal.company_id.id,
#                 'state': ,
                'balance_end_real': cfile.t8_end_balance,
                'coda_note': coda_note,
                'fys_file_id': fys_file_id,
                }, context=context)
            sequence = 0
            for lines2 in cfile.lines2_ids:
                sequence += 1
                ref = lines2.t21_seq_nbr + lines2.t21_det_nbr
                type = 'normal'
                name3 = ''
                t31_struct_type = None
                for lines3 in lines2.lines3_ids:
                    ref = lines2.t21_seq_nbr + lines3.t31_det_nbr
                    type = 'information'
                    name3 = ''.join(filter(None, [lines3.t31_free_comm,lines3.t32_free_comm, lines3.t33_free_comm]))
                    t31_struct_type = lines3.t31_struct_type
                if lines2.t21_glob > 0:
                    type = 'globalisation'
                partner = None
                partner_id = None
                invoice_id = False
                invoice = None
                account = temporaryaccount
                transaction_type = 'general'
                structcomm_message = None
                if lines2.t21_struct_type in ('101','102'):
                    structcomm_message = '+++' + lines2.t21_struct_comm[0:3] + '/' +  lines2.t21_struct_comm[3:7] + '/' +  lines2.t21_struct_comm[7:12] + '+++'
#                     print 'structcomm_message : ', structcomm_message
                name = "\n".join(filter(None, [lines2.t23_partner, structcomm_message, lines2.t21_free_comm, lines2.t22_free_comm, lines2.t23_free_comm, name3]))
                note=[]
                voucher_id = None

                if type == 'information':
                    coda_note = "\n".join([coda_note, type + ' with Ref. ' + ref, 'Date: ' + lines2.t21_date_booking, 'Communication: ' + name, ''])
                elif type == 'communication':
                    coda_note = "\n".join([coda_note, type + ' with Ref. ' + ref, 'Communication: ' + name, ''])
                
                if t31_struct_type == '001':
                    note.append(_('Counter Party') + ': ' + lines3.t31_struct_comm)
                    if lines2.t23_account_nbr:
                        note.append(_('Counter Party Account') + ': ' + lines2.t23_account_nbr)
                    if lines3.t32_free_comm:
                        note.append(_('Counter Party Address') + ': ' + lines3.t32_free_comm)
                if t31_struct_type != '001' and lines2.t23_partner:
                        note.append(_('Counter Party') + ': ' + lines2.t23_partner)
                        if lines2.t23_account_nbr:
                            note.append(_('Counter Party Account') + ': ' + lines2.t23_account_nbr)

                move_line = None
# search move_line to reconcile                
                if lines2.t22_ref_cust:
#                     print 'ref cust: ', lines2.t22_ref_cust
                    ids = pay_line_obj.search(cr, uid,[('name', '=', lines2.t22_ref_cust)])
                    if ids:
                        payment_line = pay_line_obj.browse(cr, uid, ids[0])
                        if payment_line.move_line_id and not(payment_line.move_line_id.reconcile_id):
                            move_line = move_line_obj.browse(cr, uid, payment_line.move_line_id.id)
                if lines2.t21_struct and lines2.t21_struct_type in ('101','102') and not(move_line):
#                     print structcomm_message
                    ids = move_line_obj.search(cr, uid, [('ref'.replace('%','').replace(' ',''), '=', structcomm_message), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
                    if ids:
                        move_line = move_line_obj.browse(cr, uid, ids[0])
                    
                if move_line:
# line to reconcile found                        
                    partner = move_line.partner_id
                    partner_id = partner.id
                    account = move_line.account_id.id
                    reconcile = move_line.id
                    if move_line.invoice_line_id:
                        invoice_id = move_line.invoice_line_id.invoice_id.id
                    else:
                        ids = invoice_obj.search(cr, uid, [('name', '=', move_line.move_id.name)])
                        if ids:
                            invoice_id = invoice_obj.browse(cr, uid, ids[0])
                    if move_line.credit == 0.00:
                        transaction_type = 'customer'
                    else:
                        transaction_type = 'supplier'
                    if invoice_id:
                        if invoice_id.type in ['in_invoice','in_refund']:
                            transaction_type = 'supplier'
                        else:
                            transaction_type = 'customer'                                    
                    voucher_vals = {
                        'type': transaction_type == 'supplier' and 'payment' or 'receipt',
                        'name': name,
                        'partner_id': partner_id,
                        'journal_id': journal.id,
                        'account_id': journal.default_credit_account_id.id,
                        'company_id': journal.company_id.id,
                        'currency_id': journal.company_id.currency_id.id,
                        'date': lines2.t21_date_booking,
                        'amount': abs(lines2.t21_amount),
                        'period_id': period_id[0],
                        'invoice_id': invoice_id,
                     }
                    context['invoice_id'] = invoice_id
                    voucher_vals.update(self.pool.get('account.voucher').onchange_partner_id(cr, uid, [],
                        partner_id = partner_id,
                        journal_id = journal.id,
                        amount = abs(lines2.t21_amount),
                        currency_id = journal.company_id.currency_id.id,
                        ttype = transaction_type == 'supplier' and 'payment' or 'receipt',
                        date = lines2.t21_date_booking,
                        context = context
                    )['value'])
                    line_drs = []
                    for line_dr in voucher_vals['line_dr_ids']:
                        line_drs.append((0, 0, line_dr))
                    voucher_vals['line_dr_ids'] = line_drs
                    line_crs = []
                    for line_cr in voucher_vals['line_cr_ids']:
                        line_crs.append((0, 0, line_cr))
                    voucher_vals['line_cr_ids'] = line_crs
                    voucher_id = self.pool.get('account.voucher').create(cr, uid, voucher_vals, context=context)
                   
                if lines2.t23_account_nbr:
                    ids = partner_obj.search(cr, uid, [('acc_number', '=', lines2.t23_account_nbr)])
                    if ids and len(ids) > 0:
                        partner = partner_obj.browse(cr, uid, ids[0], context=context).partner_id
                        if not(partner_id):
                            partner_id = partner.id
                        if not move_line:
# CHANGE TO DERIVATION OF STANDARD PROPOSED RECONCILATION ACCOUNT AND TRANSACTION TYPE
                            if partner.customer and not (partner.supplier):
                                account = partner.property_account_receivable.id
                                transaction_type = 'customer'
                            elif partner.supplier and not (partner.customer):
                                account = partner.property_account_payable.id
                                transaction_type = 'supplier'
                
                    
                stat_line_id = stat_line_obj.create(cr, uid, {
                      'ref': ref,
                      'statement_id': stat_id,
                      'sequence': sequence,
                      'type': transaction_type,
                      'company_id': journal.company_id.id,
                      'note': "\n".join(note),
                      'journal_id': journal_id,
                      'amount': lines2.t21_amount,
                      'date': lines2.t21_date,
                      'partner_id': partner_id,
                      'account_id': account,
                      'voucher_id': voucher_id,
                      'coda_account_number': lines2.t23_account_nbr,
                      'transaction_code': lines2.t21_code,
                      'fleet_id': None,
                      'employee_id': None,
                      'asset_id': None,
                      'state': 'draft',
                      'structcomm_flag': lines2.t21_struct,
                      'structcomm_message': structcomm_message,
                      'name': name,
                      'lines2_id': lines2.id,
                      }, context=context)
#  if Sepa Direct Debit and payment is refused create a coda_sdd_reference record 
#                 if lines2.t21_struct:
#                     print 'type: ', lines2.t21_struct_type, ' ' , lines2.t21_struct_comm             
                    
#                 if lines2.t21_struct_type == '127' and lines2.t21_struct_comm[8:9] != '0':
#                     sdd_struct = ''.join(filter(None, [lines2.t21_struct_comm, lines2.t22_free_comm, lines2.t23_free_comm]))
#                     ids_mandate=[]
#                     ids_mandate = sdd_mandate_obj.search(cr, uid,[('unique_mandate_reference', '=' , sdd_struct[44:79].rstrip())])                                    
#                     id_mandate = None
#                     if ids_mandate:
#                         id_mandate = ids_mandate[0]
#                     sdd_ref_id = sdd_ref_obj.create(cr, uid, {
#                       'lines2_id': lines2.id,
#                       'stat_id': stat_id,
#                       'date': sdd_struct[4:6] + sdd_struct[2:4] + sdd_struct[0:2],
#                       'partner_id': partner_id,
#                       'sdd_mandate_id': id_mandate,
#                       'type': sdd_struct[6:7],
#                       'scheme': sdd_struct[7:8],
#                       'pay_reason': sdd_struct[8:9],
#                       'partner': sdd_struct[9:44],
#                       'mandate_ref': sdd_struct[44:79],
#                       'comm': sdd_struct[79:141],
#                       'type_R': sdd_struct[141:142],
#                       'reason': sdd_struct[142:145],
#                       }, context=context)
#                 if lines2.t21_struct_type == '107' and lines2.t21_struct_comm[48:49] != '0':
#                     sdd_struct = ''.join(filter(None, [lines2.t21_struct_comm, lines2.t22_free_comm, lines2.t23_free_comm]))
#                     ids_mandate=[]
#                     ids_mandate = sdd_mandate_obj.search(cr, uid,[('original_mandate_identification', '=' , 'DOM80' + sdd_struct[0:12])])                                    
#                     id_mandate = None
#                     if ids_mandate:
#                         id_mandate = ids_mandate[0]
#                     sdd_ref_id = sdd_ref_obj.create(cr, uid, {
#                       'lines2_id': lines2.id,
#                       'stat_id': stat_id,
#                       'date': sdd_struct[16:18] + sdd_struct[14:16] + sdd_struct[12:14],
#                       'partner_id': partner_id,
#                       'sdd_mandate_id': id_mandate,
# #                       'type': ,
# #                       'scheme': ,
#                       'pay_reason': sdd_struct[48:49],
# #                       'partner': ,
#                       'mandate_ref': sdd_struct[0:12],
#                       'comm': sdd_struct[18:48],
# #                       'type_R': ,
# #                       'reason': ,
#                       }, context=context)
#                 
# #                 print lines2.det2_ids
                    
                for det2 in lines2.det2_ids:
#                     if det2.t21_struct:
#                         print 'type: ', det2.t21_struct_type, ' ' , det2.t21_struct_comm             
                        
#                     if det2.t21_struct_type == '127' and det2.t21_struct_comm[8:9] != '0':
#                         sdd_struct = ''.join(filter(None, [det2.t21_struct_comm, det2.t22_free_comm, det2.t23_free_comm]))
#                         ids_mandate=[]
#                         ids_mandate = sdd_mandate_obj.search(cr, uid,[('unique_mandate_reference', '=' , sdd_struct[44:79].rstrip())])                                    
#                         id_mandate = None
#                         if ids_mandate:
#                             id_mandate = ids_mandate[0]
#                         sdd_ref_id = sdd_ref_obj.create(cr, uid, {
#                           'lines2_id': det2.lines2_id.id,
#                           'stat_id': stat_id,
#                           'date': sdd_struct[4:6] + sdd_struct[2:4] + sdd_struct[0:2],
#                           'partner_id': partner_id,
#                           'sdd_mandate_id': id_mandate,
#                           'type': sdd_struct[6:7],
#                           'scheme': sdd_struct[7:8],
#                           'pay_reason': sdd_struct[8:9],
#                           'partner': sdd_struct[9:44],
#                           'mandate_ref': sdd_struct[44:79],
#                           'comm': sdd_struct[79:141],
#                           'type_R': sdd_struct[141:142],
#                           'reason': sdd_struct[142:145],
#                           }, context=context)
#                     if det2.t21_struct_type == '107' and det2.t21_struct_comm[48:49] != '0':
#                         sdd_struct = ''.join(filter(None, [det2.t21_struct_comm, det2.t22_free_comm, det2.t23_free_comm]))
#                         ids_mandate=[]
#                         ids_mandate = sdd_mandate_obj.search(cr, uid,[('original_mandate_identification', '=' , 'DOM80' + sdd_struct[0:12])])                                    
#                         id_mandate = None
#                         if ids_mandate:
#                             id_mandate = ids_mandate[0]
#                         sdd_ref_id = sdd_ref_obj.create(cr, uid, {
#                           'lines2_id': det2.lines2_id.id,
#                           'stat_id': stat_id,
#                           'date': sdd_struct[16:18] + sdd_struct[14:16] + sdd_struct[12:14],
#                           'partner_id': partner_id,
#                           'sdd_mandate_id': id_mandate,
#     #                       'type': ,
#     #                       'scheme': ,
#                           'pay_reason': sdd_struct[48:49],
#     #                       'partner': ,
#                           'mandate_ref': sdd_struct[0:12],
#                           'comm': sdd_struct[18:48],
#     #                       'type_R': ,
#     #                       'reason': ,
#                           }, context=context)
                    
                    
                    det2_obj.write(cr, uid, [det2.id], {
                        'stat_id': stat_id,
                        'stat_line_id': stat_line_id,
                        }, context=context)
                    for det3 in det2.det3_ids:
                        det3_obj.write(cr, uid, [det3.id], {
                            'stat_id': stat_id,
                            'stat_line_id': stat_line_id,
                            }, context=context)
                        
#             for free_message in file.free_message_ids:
#                 type = 'communication'        
            if coda_note != '':
                stat_obj.write(cr, uid, [stat_id], {
                    'coda_note': coda_note
                    }, context=context)
   
#         year_statement = ''
#         statements = []
#          
#         for line in recordlist:
#             if not line:
#                 pass
#             elif line[0] == '0':
#                 #Begin of a new Bank statement
#                 statement = {}
#                 statements.append(statement)
#                 statement['version'] = line[127]
#                 if statement['version'] not in ['1', '2']:
#                     raise osv.except_osv(_('Error') + ' R001', _('CODA V%s statements are not supported, please contact your bank') % statement['version'])
#                 statement['globalisation_stack'] = []
#                 statement['lines'] = []
#                 statement['date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[5:11]), '%d%m%y'))
#                 year_statement = line[9:11]
#                 statement['separateApplication'] = rmspaces(line[83:88])
#             elif line[0] == '1':
#                 #Statement details
#                 if statement['version'] == '1':
#                     statement['acc_number'] = rmspaces(line[5:17])
#                     statement['currency'] = rmspaces(line[18:21])
#                 elif statement['version'] == '2':
#                     if line[1] == '0':  # Belgian bank account BBAN structure
#                         statement['acc_number'] = rmspaces(line[5:17])
#                         statement['currency'] = rmspaces(line[18:21])
#                     elif line[1] == '1':  # foreign bank account BBAN structure
#                         raise osv.except_osv(_('Error') + ' R1001', _('Foreign bank accounts with BBAN structure are not supported '))
#                     elif line[1] == '2':    # Belgian bank account IBAN structure
#                         statement['acc_number'] = rmspaces(line[5:21])
#                         statement['currency'] = rmspaces(line[39:42])
#                     elif line[1] == '3':    # foreign bank account IBAN structure
#                         raise osv.except_osv(_('Error') + ' R1002', _('Foreign bank accounts with IBAN structure are not supported '))
#                     else:  # Something else, not supported
#                         raise osv.except_osv(_('Error') + ' R1003', _('Unsupported bank account structure '))
#                 statement['journal_id'] = False
#                 statement['bank_account'] = False
#                 # Belgian Account Numbers are composed of 12 digits.
#                 # In OpenERP, the user can fill the bank number in any format: With or without IBan code, with or without spaces, with or without '-'
#                 # The two following sql requests handle those cases.
#                 if len(statement['acc_number']) >= 12:
#                     # If the Account Number is >= 12 digits, it is mostlikely a Belgian Account Number (With or without IBAN).
#                     # The following request try to find the Account Number using a 'like' operator.
#                     # So, if the Account Number is stored with IBAN code, it can be found thanks to this.
#                     cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') like %s", ('%' + statement['acc_number'] + '%',))
#                 else:
#                     # This case is necessary to avoid cases like the Account Number in the CODA file is set to a single or few digits,
#                     # and so a 'like' operator would return the first account number in the database which matches.
#                     cr.execute("select id from res_partner_bank where replace(replace(acc_number,' ',''),'-','') = %s", (statement['acc_number'],))
#                 bank_ids = [id[0] for id in cr.fetchall()]
#                 # Filter bank accounts which are not allowed
#                 bank_ids = self.pool.get('res.partner.bank').search(cr, uid, [('id', 'in', bank_ids)])
#                 if bank_ids and len(bank_ids) > 0:
#                     bank_accs = self.pool.get('res.partner.bank').browse(cr, uid, bank_ids)
#                     for bank_acc in bank_accs:
#                         if bank_acc.journal_id.id and ((bank_acc.journal_id.currency.id and bank_acc.journal_id.currency.name == statement['currency']) or (not bank_acc.journal_id.currency.id and bank_acc.journal_id.company_id.currency_id.name == statement['currency'])):
#                             statement['journal_id'] = bank_acc.journal_id
#                             statement['bank_account'] = bank_acc
#                             break
#                 if not statement['bank_account']:
#                     raise osv.except_osv(_('Error') + ' R1004', _("No matching Bank Account (with Account Journal) found.\n\nPlease set-up a Bank Account with as Account Number '%s' and as Currency '%s' and an Account Journal.") % (statement['acc_number'], statement['currency']))
#                 statement['description'] = rmspaces(line[90:125])
#                 statement['balance_start'] = float(rmspaces(line[43:58])) / 1000
#                 if line[42] == '1':    #1 = Debit, the starting balance is negative
#                     statement['balance_start'] = - statement['balance_start']
#                 statement['balance_start_date'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[58:64]), '%d%m%y'))
#                 statement['accountHolder'] = rmspaces(line[64:90])
#                 statement['paperSeqNumber'] = year_statement + '-' + line[9:9] + line[19:20] + '-' + rmspaces(line[2:4])
#                 statement['codaSeqNumber'] = rmspaces(line[126:128])
#             elif line[0] == '2':
#                 if line[1] == '1' and line[6:10] == '0000':
#                     #New statement line
#                     statementLine = {}
#                     statementLine['ref'] = rmspaces(line[2:10])
#                     statementLine['ref_move'] = rmspaces(line[2:6])
#                     statementLine['ref_move_detail'] = rmspaces(line[6:10])
#                     statementLine['sequence'] = len(statement['lines']) + 1
#                     statementLine['transactionRef'] = rmspaces(line[10:31])
#                     statementLine['debit'] = line[31]  # 0 = Credit, 1 = Debit
#                     statementLine['amount'] = float(rmspaces(line[32:47])) / 1000
#                     if statementLine['debit'] == '1':
#                         statementLine['amount'] = - statementLine['amount']
#                     statementLine['transaction_type'] = line[53]
#                     statementLine['transactionDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[47:53]), '%d%m%y'))
#                     statementLine['transaction_family'] = rmspaces(line[54:56])
#                     statementLine['transaction_code'] = rmspaces(line[56:58])
#                     statementLine['transaction_category'] = rmspaces(line[58:61])
# 1 line added for NP transaction code improvement
#                     statementLine['np_transaction_code'] = rmspaces(line[54:62])
#                     if line[61] == '1':
#                         #Structured communication
#                         statementLine['communication_struct'] = True
#                         statementLine['communication_type'] = line[62:65]
#                         statementLine['communication'] = '+++' + line[65:68] + '/' + line[68:72] + '/' + line[72:77] + '+++'
#                     else:
#                         #Non-structured communication
#                         statementLine['communication_struct'] = False
#                         statementLine['communication'] = rmspaces(line[62:115])
#                     statementLine['entryDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[115:121]), '%d%m%y'))
#                     statementLine['type'] = 'normal'
#                     statementLine['globalisation'] = int(line[124])
#                     if len(statement['globalisation_stack']) > 0 and statementLine['communication'] != '':
#                         statementLine['communication'] = "\n".join([statement['globalisation_stack'][-1]['communication'], statementLine['communication']])
#                     if statementLine['globalisation'] > 0:
#                         if len(statement['globalisation_stack']) > 0 and statement['globalisation_stack'][-1]['globalisation'] == statementLine['globalisation']:
#                             # Destack
#                             statement['globalisation_stack'].pop()
#                         else:
#                             #Stack
#                             statementLine['type'] = 'globalisation'
#                             statement['globalisation_stack'].append(statementLine)
#                     statement['lines'].append(statementLine)
#                 elif line[1] == '2':
#                     if statement['lines'][-1]['ref'][0:4] != line[2:6]:
#                         raise osv.except_osv(_('Error') + 'R2004', _('CODA parsing error on movement data record 2.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
#                     if line[6:10] == '0000':
#                         statement['lines'][-1]['communication'] += rmspaces(line[10:63])
#                         statement['lines'][-1]['payment_reference'] = rmspaces(line[63:98])
#                         statement['lines'][-1]['counterparty_bic'] = rmspaces(line[98:109])
#                 elif line[1] == '3':
#                     if statement['lines'][-1]['ref'][0:4] != line[2:6]:
#                         raise osv.except_osv(_('Error') + 'R2005', _('CODA parsing error on movement data record 2.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
#                     if statement['version'] == '1':
#                         statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
#                         statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:73])
#                         statement['lines'][-1]['counterpartyAddress'] = rmspaces(line[73:125])
#                         statement['lines'][-1]['counterpartyCurrency'] = ''
#                     else:
#                         if line[22] == ' ':
#                             statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:22])
#                             statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[23:26])
#                         else:
#                             statement['lines'][-1]['counterpartyNumber'] = rmspaces(line[10:44])
#                             statement['lines'][-1]['counterpartyCurrency'] = rmspaces(line[44:47])
#                         statement['lines'][-1]['counterpartyName'] = rmspaces(line[47:82])
#                         statement['lines'][-1]['communication'] += rmspaces(line[82:125])
#                elif (line[1] != '1' or line[125] != '0'):
#                    # movement data record 2.x (x != 1,2,3)
#                    raise osv.except_osv(_('Error') + 'R2006', _('\nMovement data records of type 2.%s are not supported ') % line[1])
#             elif line[0] == '3':
#                 if line[1] == '1':
#                     infoLine = {}
#                     infoLine['entryDate'] = statement['lines'][-1]['entryDate']
#                     infoLine['type'] = 'information'
#                     infoLine['sequence'] = len(statement['lines']) + 1
#                     infoLine['ref'] = rmspaces(line[2:10])
#                     infoLine['transactionRef'] = rmspaces(line[10:31])
#                     infoLine['transaction_type'] = line[31]
#                     infoLine['transaction_family'] = rmspaces(line[32:34])
#                     infoLine['transaction_code'] = rmspaces(line[34:36])
#                     infoLine['transaction_category'] = rmspaces(line[36:39])
#                     infoLine['communication'] = rmspaces(line[40:113])
#                     statement['lines'].append(infoLine)
#                 elif line[1] == '2':
#                     if infoLine['ref'] != rmspaces(line[2:10]):
#                         raise osv.except_osv(_('Error') + 'R3004', _('CODA parsing error on information data record 3.2, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
#                     statement['lines'][-1]['communication'] += rmspaces(line[10:100])
#                 elif line[1] == '3':
#                     if infoLine['ref'] != rmspaces(line[2:10]):
#                         raise osv.except_osv(_('Error') + 'R3005', _('CODA parsing error on information data record 3.3, seq nr %s! Please report this issue via your OpenERP support channel.') % line[2:10])
#                     statement['lines'][-1]['communication'] += rmspaces(line[10:100])
#             elif line[0] == '4':
#                     comm_line = {}
#                     comm_line['type'] = 'communication'
#                     comm_line['sequence'] = len(statement['lines']) + 1
#                     comm_line['ref'] = rmspaces(line[2:10])
#                     comm_line['communication'] = rmspaces(line[32:112])
#                     statement['lines'].append(comm_line)
#             elif line[0] == '8':
#                 # new balance record
#                 statement['debit'] = line[41]
#                 statement['paperSeqNumber'] = year_statement + '-' + line[8:9] + line[18:20] + '-' + rmspaces(line[1:4])
#                 statement['balance_end_real'] = float(rmspaces(line[42:57])) / 1000
#                 statement['balance_end_realDate'] = time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT, time.strptime(rmspaces(line[57:63]), '%d%m%y'))
#                 if statement['debit'] == '1':    # 1=Debit
#                     statement['balance_end_real'] = - statement['balance_end_real']
#                 if statement['balance_end_realDate']:
#                     period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', statement['journal_id'].company_id.id), ('date_start', '<=', statement['balance_end_realDate']), ('date_stop', '>=', statement['balance_end_realDate'])])
#                 else:
#                     period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', statement['journal_id'].company_id.id), ('date_start', '<=', statement['date']), ('date_stop', '>=', statement['date'])])
#                 if not period_id and len(period_id) == 0:
#                     raise osv.except_osv(_('Error') + 'R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s for the company %s.") % (statement['balance_end_realDate'], statement['journal_id'].company_id.name))
#                 statement['period_id'] = period_id[0]
#             elif line[0] == '9':
#                 statement['balanceMin'] = float(rmspaces(line[22:37])) / 1000
#                 statement['balancePlus'] = float(rmspaces(line[37:52])) / 1000
#                 if not statement.get('balance_end_real'):
#                     statement['balance_end_real'] = statement['balance_start'] + statement['balancePlus'] - statement['balanceMin']
#         for i, statement in enumerate(statements):
#             statement['coda_note'] = ''
#             balance_start_check_date = (len(statement['lines']) > 0 and statement['lines'][0]['entryDate']) or statement['date']
#             cr.execute('SELECT balance_end_real \
#                 FROM account_bank_statement \
#                 WHERE journal_id = %s and date <= %s \
#                 ORDER BY date DESC,id DESC LIMIT 1', (statement['journal_id'].id, balance_start_check_date))
#             res = cr.fetchone()
#             balance_start_check = res and res[0]
#             if balance_start_check == None:
#                 if statement['journal_id'].default_debit_account_id and (statement['journal_id'].default_credit_account_id == statement['journal_id'].default_debit_account_id):
#                     balance_start_check = statement['journal_id'].default_debit_account_id.balance
#                 else:
#                     raise osv.except_osv(_('Error'), _("Configuration Error in journal %s!\nPlease verify the Default Debit and Credit Account settings.") % statement['journal_id'].name)
#             if balance_start_check != statement['balance_start']:
#                 statement['coda_note'] = _("The CODA Statement %s Starting Balance (%.2f) does not correspond with the previous Closing Balance (%.2f) in journal %s!") % (statement['description'] + ' #' + statement['paperSeqNumber'], statement['balance_start'], balance_start_check, statement['journal_id'].name)
#             if not(statement.get('period_id')):
#                 raise osv.except_osv(_('Error') + ' R3006', _(' No transactions or no period in coda file !'))
#             data = {
#                 'name': statement['paperSeqNumber'],
#                 'date': statement['date'],
#                 'journal_id': statement['journal_id'].id,
#                 'period_id': statement['period_id'],
#                 'balance_start': statement['balance_start'],
#                 'balance_end_real': statement['balance_end_real'],
#             }
#  
#             ids = self.pool.get('account.bank.statement').search(cr, uid, [('name', '=', statement['paperSeqNumber'])])
#             if ids:
#                 raise osv.except_osv(_('Error'), _('CODA messsage already imported!'))
#  
#             statement['id'] = self.pool.get('account.bank.statement').create(cr, uid, data, context=context)
#             for line in statement['lines']:
#                 if line['type'] == 'information':
#                     statement['coda_note'] = "\n".join([statement['coda_note'], line['type'].title() + ' with Ref. ' + str(line['ref']), 'Date: ' + str(line['entryDate']), 'Communication: ' + line['communication'], ''])
#                 elif line['type'] == 'communication':
#                     statement['coda_note'] = "\n".join([statement['coda_note'], line['type'].title() + ' with Ref. ' + str(line['ref']), 'Ref: ', 'Communication: ' + line['communication'], ''])
#                 elif line['type'] == 'normal' or line['type'] == 'globalisation':
#                     note = []
#                     if 'counterpartyName' in line and line['counterpartyName'] != '':
#                         note.append(_('Counter Party') + ': ' + line['counterpartyName'])
#                     else:
#                         line['counterpartyName'] = False
#                     if 'counterpartyNumber' in line and line['counterpartyNumber'] != '':
#                         try:
#                             if int(line['counterpartyNumber']) == 0:
#                                 line['counterpartyNumber'] = False
#                         except:
#                             pass
#                         if line['counterpartyNumber']:
#                             note.append(_('Counter Party Account') + ': ' + line['counterpartyNumber'])
#                     else:
#                         line['counterpartyNumber'] = False
#  
#                     if 'counterpartyAddress' in line and line['counterpartyAddress'] != '':
#                         note.append(_('Counter Party Address') + ': ' + line['counterpartyAddress'])
#                     line['name'] = "\n".join(filter(None, [line['counterpartyName'], line['communication']]))
#                     line['transaction_type'] = 'general'
#                     partner = None
#                     partner_id = None
#                     invoice = False
#                     if line['communication_struct'] and 'communication_type' in line and line['communication_type'] == '101':
#                         ids = self.pool.get('account.invoice').search(cr, uid, [('reference', '=', line['communication']), ('reference_type', '=', 'bba')])
#                         if ids:
#                             invoice = self.pool.get('account.invoice').browse(cr, uid, ids[0])
#                             partner = invoice.partner_id
#                             partner_id = partner.id
#                             if invoice.type in ['in_invoice', 'in_refund'] and line['debit'] == '1':
#                                 line['transaction_type'] = 'supplier'
#                             elif invoice.type in ['out_invoice', 'out_refund'] and line['debit'] == '0':
#                                 line['transaction_type'] = 'customer'
#                             line['account'] = invoice.account_id.id
#                             line['reconcile'] = False
#                             if invoice.type in ['in_invoice', 'out_invoice']:
#                                 iml_ids = self.pool.get('account.move.line').search(cr, uid, [('move_id', '=', invoice.move_id.id), ('reconcile_id', '=', False), ('account_id.reconcile', '=', True)])
#                             if iml_ids:
#                                 line['reconcile'] = iml_ids[0]
#                             if line['reconcile']:
#                                 voucher_vals = {
#                                     'type': line['transaction_type'] == 'supplier' and 'payment' or 'receipt',
#                                     'name': line['name'],
#                                     'partner_id': partner_id,
#                                     'journal_id': statement['journal_id'].id,
#                                     'account_id': statement['journal_id'].default_credit_account_id.id,
#                                     'company_id': statement['journal_id'].company_id.id,
#                                     'currency_id': statement['journal_id'].company_id.currency_id.id,
#                                     'date': line['entryDate'],
#                                     'amount': abs(line['amount']),
#                                     'period_id': statement['period_id'],
#                                     'invoice_id': invoice.id,
#                                 }
#                                 context['invoice_id'] = invoice.id
#                                 voucher_vals.update(self.pool.get('account.voucher').onchange_partner_id(cr, uid, [],
#                                     partner_id=partner_id,
#                                     journal_id=statement['journal_id'].id,
#                                     amount=abs(line['amount']),
#                                     currency_id=statement['journal_id'].company_id.currency_id.id,
#                                     ttype=line['transaction_type'] == 'supplier' and 'payment' or 'receipt',
#                                     date=line['transactionDate'],
#                                     context=context
#                                 )['value'])
#                                 line_drs = []
#                                 for line_dr in voucher_vals['line_dr_ids']:
#                                     line_drs.append((0, 0, line_dr))
#                                 voucher_vals['line_dr_ids'] = line_drs
#                                 line_crs = []
#                                 for line_cr in voucher_vals['line_cr_ids']:
#                                     line_crs.append((0, 0, line_cr))
#                                 voucher_vals['line_cr_ids'] = line_crs
#                                 line['voucher_id'] = self.pool.get('account.voucher').create(cr, uid, voucher_vals, context=context)
#                     if 'counterpartyNumber' in line and line['counterpartyNumber']:
#                         ids = self.pool.get('res.partner.bank').search(cr, uid, [('acc_number', '=', str(line['counterpartyNumber']))])
#                         if ids and len(ids) > 0:
#                             partner = self.pool.get('res.partner.bank').browse(cr, uid, ids[0], context=context).partner_id
#                             partner_id = partner.id
#                             if not invoice:
# CHANGE TO DERIVATION OF STANDARD PROPOSED RECONCILATION ACCOUNT AND TRANSACTION TYPE
#                                 if partner.customer and not (partner.supplier):
#                                     line['account'] = partner.property_account_receivable.id
#                                     line['transaction_type'] = 'customer'
#                                 elif partner.supplier and not (partner.customer):
#                                     line['account'] = partner.property_account_payable.id
#                                     line['transaction_type'] = 'supplier'
#                                 else:
#                                     line['account'] = temporaryaccount
#                                     line['transaction_type'] = 'general'
#                                if line['debit'] == '0':
#                                    line['account'] = partner.property_account_receivable.id
#                                    if partner.customer:
#                                        line['transaction_type'] = 'customer'
#                                elif line['debit'] == '1':
#                                    line['account'] = partner.property_account_payable.id
#                                    if partner.supplier:
#                                        line['transaction_type'] = 'supplier'
#                     if not partner and not invoice:
#                         line['account'] = temporaryaccount
#                     if 'communication' in line and line['communication'] != '':
#                         note.append(_('Communication') + ': ' + line['communication'])
#                     if 'voucher_id' not in line:
#                         line['voucher_id'] = None
#                     if line['communication_struct']:
#                         structcomm_message = line['communication']
#                     else:
#                         structcomm_message = ''
#                     data = {
#                         'name': line['name'],
#                         'note':  "\n".join(note),
#                         'date': line['entryDate'],
#                         'amount': line['amount'],
#                         'type': line['transaction_type'],
#                         'partner_id': partner_id,
#                         'account_id': line['account'],
#                         'statement_id': statement['id'],
#                         'ref': line['ref'],
#                         'sequence': line['sequence'],
#                         'voucher_id': line['voucher_id'],
#                         'coda_account_number': line['counterpartyNumber'],
# # 1 line added for NP transaction code improvement
#                         'transaction_code': line['np_transaction_code'],
#                         'structcomm_flag': line['communication_struct'],
#                         'structcomm_message': structcomm_message,
#                     }
#                     self.pool.get('account.bank.statement.line').create(cr, uid, data, context=context)
#             if statement['coda_note'] != '':
#                 self.pool.get('account.bank.statement').write(cr, uid, [statement['id']], {'coda_note': statement['coda_note']}, context=context)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'action_bank_statement_tree')
        action = self.pool.get(model).browse(cr, uid, action_id, context=context)
        return {
            'name': action.name,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'res_model': action.res_model,
            'domain': action.domain,
            'context': action.context,
            'type': 'ir.actions.act_window',
            'search_view_id': action.search_view_id.id,
            'views': [(v.view_id.id, v.view_mode) for v in action.view_ids]
        }

def rmspaces(s):
    return " ".join(s.split())

account_coda_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:# -*- coding: utf-8 -*-

