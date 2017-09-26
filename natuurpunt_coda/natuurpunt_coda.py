#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
# 
##############################################################################
import base64
import datetime, time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp import tools
from md5 import md5
import re
from natuurpunt_tools import koalect_webservice

import logging

_logger = logging.getLogger(__name__)

def parse_koalect_free_comm(free_comm):
    split_free_comm = re.split(r'[ ](?=[^0-9])', free_comm)[1].split(' ')
    if len(split_free_comm) > 1:
        koalect_comm = split_free_comm[0]
        koalect_id = int(split_free_comm[1])
    else:
        koalect_comm = False
        koalect_id = int(split_free_comm[0])
    return koalect_comm, koalect_id

def consume_webservices(webservices):
    return reduce(lambda f,g : lambda x: g(f(x)),map(lambda x : x.values()[0], webservices))

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

    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        res = {}
        if not('last_line' in context) or ('last_line' in context and context['last_line']):
# 	    print 'END_BALANCE'
	    for statement in self.browse(cursor, user, ids, context=context):
	        res[statement.id] = statement.balance_start
	        for line in statement.line_ids:
	            res[statement.id] += line.amount
        return res

    def _get_statement(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.bank.statement.line').browse(cr, uid, ids, context=context):
            result[line.statement_id.id] = True
        return result.keys()
    
    _columns = {
	'balance_end': fields.function(_end_balance,
	    store = {
		'account.bank.statement': (lambda self, cr, uid, ids, c={}: ids, ['line_ids','move_line_ids','balance_start'], 10),
		'account.bank.statement.line': (_get_statement, ['amount'], 10),
	    },
	    string="Computed Balance", help='Balance as calculated based on Starting Balance and transaction lines'),
        'fys_file_id': fields.many2one('account.coda.fys.file', 'Fys. File', select=True),
        'det2_ids': fields.one2many('account.coda.det2', 'stat_id', 'Coda Detail Lines'),
        'det3_ids': fields.one2many('account.coda.det3', 'stat_id', 'Coda Detail Information'),
        'sdd_ref_ids': fields.one2many('account.coda.sdd.refused', 'stat_id', 'SDD Refused'),
               }
    
    def unlink(self, cr, uid, ids, context=None):
        """base override unlink"""
        for this in self.browse(cr, uid, ids, context):
            if this.fys_file_id:
                this.fys_file_id.write(
                        {'filename': this.fys_file_id.id,
                        })
                this.fys_file_id.refresh()
        stat = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids = []
        for t in stat:
            if t['state'] in ('draft','error'):
                unlink_ids.append(t['id'])
            else:
                raise osv.except_osv(_('Invalid Action!'), _('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True
    
account_bank_statement()
    
class account_bank_statement_line(osv.osv):
    _inherit = 'account.bank.statement.line'

    def create(self, cr, uid, vals, context=None):
        coda_id = 0
        
        if 'move_flag' not in vals or not vals['move_flag']:
# New analytic code contract, fonds, project
            if 'name_zonder_adres' in vals and vals['name_zonder_adres'] and vals['type'] != 'supplier':
                
                analytic_account_obj = self.pool.get('account.analytic.account')
                acc_coda_acc_obj = self.pool.get('account.coda.account')
                
                # split omschrijving  
                omschrijving = vals['name_zonder_adres'].upper().split()
                patterns = [('^[A-Z]{3}-[0-9]{4}-[0-9]{4}',False), # kostenplaats
                            ('^P-[0-9]{2}-[0-9]{6}$',True),        # project
                            ('^F-[0-9]{5}$',True),                 # fonds
                            ('^[0-6]{6}$',False),                  # fonds
                            ('^C-[A-Z]{2}-',False),]               # contract

                analytic_res = lambda dim1,dim2,dim3: {'dim1':dim1,'dim2':dim2,'dim3':dim3}

                def apply_regex_to_omschrijving(pattern, use_group, field='code', operator='=', func=None):
                    for word in omschrijving:
                        match_obj = re.search(pattern,word)
                        if match_obj:
                            match = match_obj.group() if use_group else word
                            if match:
                                res = get_analytic_account(field,
                                                           operator,
                                                           func(match) if func else match)
                                if res:
                                    return res
                    return False

                def get_analytic_account(field, operator, match):
                    ids = analytic_account_obj.search(cr, uid,[(field, operator, match)])
                    for analytic_account in analytic_account_obj.browse(cr, uid, ids):
                        if analytic_account.dimension_id.sequence == 1:
                            return analytic_res(analytic_account.id,
                                                analytic_account.default_dimension_2_id.id,
                                                analytic_account.default_dimension_3_id.id)
                        if analytic_account.dimension_id.sequence == 2:
                            return analytic_res(analytic_account.default_dimension_1_id.id,
                                                analytic_account.id,
                                                analytic_account.default_dimension_3_id.id)
                        if analytic_account.dimension_id.sequence == 3:
                            return analytic_res(analytic_account.default_dimension_1_id.id,
                                                analytic_account.default_dimension_2_id.id,
                                                analytic_account.id)
                    return False

                for pattern_tuple in patterns:
                    pattern,use_group = pattern_tuple
                    res = apply_regex_to_omschrijving(pattern, use_group)
                    if res:
                        break

                # fallback old_code
                if not res:
                    pattern = '^[0-9]{4}'
                    res = apply_regex_to_omschrijving(pattern,False,'old_code')
                if not res:
                    pattern = '^[0-9]{4}'
                    res = apply_regex_to_omschrijving(pattern,True,'old_code')
                if not res: # Prefix string PROJECT4444, NR.4444, NR:3333
                    pattern = '^[A-Z]+.[:.]?\d{4}'
                    func = lambda match : ''.join([i for i in match if i.isdigit()])
                    res = apply_regex_to_omschrijving(pattern,True,'old_code','=ilike',func)
                if not res: #P - 10 - 000035
                    pattern = '^[0-9]{6}'
                    res = apply_regex_to_omschrijving(pattern,False,'old_code')
                if not res:
                    pattern = '^[0-9]{6}[A-Z]$'
                    func = lambda match : ''.join([i for i in match if i.isdigit()])
                    res = apply_regex_to_omschrijving(pattern,True,'old_code','=',func)

                if res:
                    ids = acc_coda_acc_obj.search(cr, uid,[('name', '=', 'Giften-afleiding')])
                    for acc_coda_acc in acc_coda_acc_obj.browse(cr, uid, ids):
                       vals['account_id'] = acc_coda_acc.account_id.id
                    vals['analytic_dimension_1_id'] = res['dim1']
                    vals['analytic_dimension_2_id'] = res['dim2']
                    vals['analytic_dimension_3_id'] = res['dim3']

# Amount
            sql_stat = 'select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id  from account_coda_account, account_bank_statement where amount <> 0 and amount = %f and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id' % (vals['amount'], vals['account_id'], vals['statement_id'], )
            cr.execute(sql_stat)
            for sql_res in cr.dictfetchall():
                vals['account_id'] = sql_res['account_id']
                vals['analytic_dimension_1_id'] = sql_res['analytic_dimension_1_id']
                vals['analytic_dimension_2_id'] = sql_res['analytic_dimension_2_id']
                vals['analytic_dimension_3_id'] = sql_res['analytic_dimension_3_id']

# Description
            if 'name_zonder_adres' in vals and vals['name_zonder_adres']:
                sql_stat = "select account_coda_account.id as coda_id, account_id, analytic_dimension_1_id, analytic_dimension_2_id, analytic_dimension_3_id  from account_coda_account, account_bank_statement where ('%s' like '%s' || communication_like || '%s') and not(communication_like IS NULL) and account_coda_account.company_id = (select company_id from account_account where account_account.id = %d) and account_bank_statement.id = %d and account_bank_statement.journal_id = account_coda_account.journal_id" % (vals['name_zonder_adres'].replace("'", ""), '%', '%', vals['account_id'], vals['statement_id'], )
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

        dims_required = self.onchange_account_id(cr, uid, 0, vals['account_id'], context=context)
        vals['analytic_dimension_1_required'] = dims_required['value']['analytic_dimension_1_required']
        vals['analytic_dimension_2_required'] = dims_required['value']['analytic_dimension_2_required']
        vals['analytic_dimension_3_required'] = dims_required['value']['analytic_dimension_3_required']
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
        'name_zonder_adres': fields.char('name zonder adres', size=128),
        'move_flag': fields.boolean('Move found'),
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

class account_coda_koalect(osv.osv):
    _name = 'account.coda.koalect'
    _description = 'Coda Line Item Koalect'

    _columns = {
        'stat_line_id': fields.many2one('account.bank.statement.line', 'Bank Statementline', select=True, ondelete='cascade'),
        'payment_method': fields.char('Betaalmethode'),
        'firstname': fields.char('Voornaam'),
        'lastname': fields.char('Achternaam'),
        'email': fields.char('E-mail'),
        'street': fields.char('Straat'),
        'number': fields.char('Huisnummer'),
        'box' : fields.char('Bus'),
        'city': fields.char('Stad'),
        'postal_code': fields.char('Postcode'),
        'country': fields.char('Land'),
        'is_tax_certificate': fields.integer('Fiscaal attest'),
        'koalect_id': fields.integer('Koalect ID'),
    }

account_coda_koalect()

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
    
    def name_search(self, cr, uid, name, args=None, operator='ilike',
                    context=None, limit=100):
        if not args:
            args = []
        args = args[:]
        ids = []
        if name:
            ids = self.search(cr, uid,
                              [('t21_bank_ref', '=like', name + "%")] + args,
                              limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t21_struct_comm', '=like', name + "%")] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t21_code', '=like', name + "%")] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t21_free_comm', operator, name)] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t22_free_comm', operator, name)] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t22_ref_cust', operator, name)] + args,
                                  limit=limit)
        else:
            ids = self.search(cr, uid, args, context=context, limit=limit)
        
        return self.name_get(cr, uid, ids, context=context) 
       
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

    def name_search(self, cr, uid, name, args=None, operator='ilike',
                    context=None, limit=100):
        if not args:
            args = []
        args = args[:]
        ids = []
        if name:
            ids = self.search(cr, uid,
                              [('t31_code', '=like', name + "%")] + args,
                              limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t31_struct_comm', operator, name)] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t31_free_comm', operator, name)] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t32_free_comm', operator, name)] + args,
                                  limit=limit)
            if not ids:
                ids = self.search(cr, uid,
                                  [('t33_free_comm', operator, name)] + args,
                                  limit=limit)
        else:
            ids = self.search(cr, uid, args, context=context, limit=limit)
        return self.name_get(cr, uid, ids, context=context) 
    
account_coda_det3()

class account_coda_sdd_refused(osv.osv):
    _name = 'account.coda.sdd.refused'
    _description = 'Coda SDD refused lines'
    
    _columns = {
        'lines2_id': fields.many2one('account.coda.lines2', 'Item line', select=True),
        'stat_id': fields.many2one('account.bank.statement', 'Bank Statement'),
        'date': fields.date('Settlement Date'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'sdd_mandate_id': fields.many2one('sdd.mandate', 'Mandate', select=True),
        'type': fields.char('Type', size=1),
        'scheme': fields.char('Scheme', size=1),
        'pay_reason': fields.char('Paid or reason', size=1),
        'partner': fields.char('Partner', size=35),
        'mandate_ref': fields.char('Referentie', size=35),
        'comm': fields.char('Communicatie'),
        'type_R': fields.char('Type R', size=1),
        'reason': fields.char('Reden'),
        'name': fields.char('Name', size=64),
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
        sdd_mandate_obj = self.pool.get('sdd.mandate')
        koalect_obj = self.pool.get('res.koalect')
        res_partner_obj = self.pool.get('res.partner')
        account_coda_koalect_obj = self.pool.get('account.coda.koalect')
 
        data_md5 = md5(codafile).digest()       
        exists = fys_file_obj.search(cr, uid, [('filename','=',data_md5)], context=context)
        if exists:
            raise osv.except_osv(_('Error'),_('Error') + _('Duplicate Coda filename'))
        fys_file_id = fys_file_obj.create(cr, uid, {'filename': data_md5}, context=context)
        
        prev = 9
        expect = 0
        counter = 0
        detail = 0
        vorige = '9999'
        for line in recordlist:
#             print line[0:10], detail, expect, prev
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
                detail = 0
                continue
            if line[0] == '2':
                if line[1] == '1':
#                     print line[2:6], vorige
                    if line[2:6] != vorige:
                        detail = 0
                        vorige = line[2:6]
                    if line[6:10] == '0000':
                        detail = 1
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
                    if struct_type in ('101','102'):
# gestructureerde detail verwerken als gewone lijn en bij de eerste de gegroepeerde lijn verwijderen
                        if detail == 1:
#                             verwijderen van de gegroepeerde lijn
                            detail = 2
                            lines2_obj.unlink(cr, uid, [lines2_id], context=context)
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
                    else:
                        detail = 0
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
                    if line[6:10] == '0000' or detail != 0:
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
                    if line[6:10] == '0000' or detail != 0:
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
            if bank_account.state != 'iban':
                raise osv.except_osv(_('Error'), _("Please set-up Bank Account as IBAN."))

            journal = journal_obj.browse(cr, uid, journal_id)
            company_id = journal.company_id.id
            currency_id = journal.company_id.currency_id.id
            default_credit_account_id = journal.default_credit_account_id.id
            if cfile.t8_end_date:
                period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', company_id), ('date_start', '<=', cfile.t8_end_date), ('date_stop', '>=', cfile.t8_end_date)])
            else:
                period_id = self.pool.get('account.period').search(cr, uid, [('company_id', '=', company_id), ('date_start', '<=', cfile.t0_date), ('date_stop', '>=', cfile.t0_date)])
            if not period_id:
                raise osv.except_osv(_('Error') + 'R0002', _("The CODA Statement New Balance date doesn't fall within a defined Accounting Period! Please create the Accounting Period for date %s for the company %s.") % (cfile.t8_end_date, journal.company_id.name))

            statName = cfile.t0_date[2:4] + '-' + bank_account.acc_number[4:5] + bank_account.acc_number[14:16] + '-' + cfile.t1_paper_seq_nbr
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
                'company_id': company_id,
#                 'state': ,
                'balance_end_real': cfile.t8_end_balance,
                'coda_note': coda_note,
                'fys_file_id': fys_file_id,
                }, context=context)
            sequence = 0
            
            used_moves = {}

            # get available koalect webservice(s), key per koalect project
            # configurable in settings > configuration > koalect
            koalect_ids = koalect_obj.search(cr, uid, [])
            koalect_webservices = []
            if koalect_ids:
                for koalect_api in koalect_obj.browse(cr, uid, koalect_ids):
                    koalect_webservices.append({koalect_api.project:koalect_webservice(koalect_api.url,koalect_api.key)})
            
#            nbr_lines = len(cfile.lines2_ids)
	    nbr_lines = 0
	    for lines2 in cfile.lines2_ids:
	    	nbr_lines += 1
            context['last_line'] = False
            for lines2 in cfile.lines2_ids:
                sequence += 1
# 		print datetime.datetime.now() , 'start ' + lines2.t21_seq_nbr + lines2.t21_det_nbr 
                ref = lines2.t21_seq_nbr + lines2.t21_det_nbr
                type = 'normal'
                name3 = ''
                name3_zonder_adres = ''
                t31_struct_type = None
                for lines3 in lines2.lines3_ids:
                    ref = lines2.t21_seq_nbr + lines3.t31_det_nbr
                    type = 'information'
                    name3 = ''.join(filter(None, [lines3.t31_free_comm,lines3.t32_free_comm, lines3.t33_free_comm]))
                    name3 = ''.join(filter(None, [lines3.t31_free_comm,lines3.t33_free_comm]))
                    t31_struct_type = lines3.t31_struct_type
                if lines2.t21_glob > 0:
                    type = 'globalisation'
                partner = None
                partner_id = None
                invoice = None
                invoice_id = None
                account = temporaryaccount
                transaction_type = 'general'
                structcomm_message = None
                if lines2.t21_struct_type in ('101','102'):
                    structcomm_message = '+++' + lines2.t21_struct_comm[0:3] + '/' +  lines2.t21_struct_comm[3:7] + '/' +  lines2.t21_struct_comm[7:12] + '+++'
#                     print 'structcomm_message : ', structcomm_message
                name = "\n".join(filter(None, [lines2.t23_partner, structcomm_message, lines2.t21_free_comm, lines2.t22_free_comm, lines2.t23_free_comm, name3]))
                name_zonder_adres = "\n".join(filter(None, [lines2.t23_partner, structcomm_message, lines2.t21_free_comm, lines2.t22_free_comm, lines2.t23_free_comm, name3_zonder_adres]))
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
                move_flag = False
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
                    invoice_ids = invoice_obj.search(cr, uid, [('reference','=',structcomm_message),('state','=','open')])
                    _logger.info("processing reference: {}".format(structcomm_message))
                    if len(invoice_ids) == 1:
                        for invoice in invoice_obj.browse(cr, uid, invoice_ids):
                            ids = move_line_obj.search(cr, uid, [('move_id','=', invoice.move_id.id),('reconcile_id', '=', False),('account_id.reconcile', '=', True)])
                            if ids:
                                move_line = move_line_obj.browse(cr, uid, ids[0])
# 		print datetime.datetime.now() , 'move gezocht '
                    
                if move_line:
                    if move_line.credit == 0.00:
                        transaction_type = 'customer'
                    else:
                        transaction_type = 'supplier'
                if move_line and (move_line.debit + move_line.credit) == abs(lines2.t21_amount):
# line to reconcile found
#
# add code to check if this move_line hasn't been used before in this statement
#
                    if not(move_line.id in used_moves):
                        used_moves[move_line.id] = [move_line.id]
                    
                    
                        move_flag = True 
                        context['move_line_ids'] = [move_line.id]                        
                        partner = move_line.partner_id
                        partner_id = partner.id
                        account = move_line.account_id.id
                        reconcile = move_line.id
                        if move_line.invoice_line_id:
                            invoice = move_line.invoice_line_id.invoice_id
                            invoice_id = invoice.id
                        else:
                            ids = invoice_obj.search(cr, uid, [('name', '=', move_line.move_id.name)])
                            if ids:
                                invoice = invoice_obj.browse(cr, uid, ids[0])
                                invoice_id = invoice.id
                        if invoice:
                            if invoice.type in ['in_invoice','in_refund']:
                                transaction_type = 'supplier'
                            else:
                                transaction_type = 'customer' 
                        voucher_vals = {
                            'type': transaction_type == 'supplier' and 'payment' or 'receipt',
                            'name': name,
                            'partner_id': partner_id,
                            'journal_id': journal_id,
                            'account_id': default_credit_account_id,
                            'company_id': company_id,
                            'currency_id': currency_id,
                            'date': lines2.t21_date_booking,
                            'amount': abs(lines2.t21_amount),
                            'line_amount': lines2.t21_amount, 
                            'period_id': period_id[0],
#                         'invoice_id': invoice_id,
                        }
                        context['invoice_id'] = invoice_id
                        voucher_vals.update(self.pool.get('account.voucher').onchange_partner_id(cr, SUPERUSER_ID, [],
                            partner_id = partner_id,
                            journal_id = journal_id,
                            amount = abs(lines2.t21_amount),
                            currency_id = currency_id,
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
# 		        print datetime.datetime.now() , 'voucher gemaakt '

                koalect_output = 0
                if lines2.t23_partner == 'MANGOPAY SA' and koalect_webservices:
                    koalect_comm, koalect_id = parse_koalect_free_comm(lines2.t21_free_comm)
                    #koalect_api  = [api for api in koalect_webservices if koalect_comm in api]
                    #koalect_data = koalect_webservices[0]['Natuurpunt giften'](koalect_id)
                    koalect_output = consume_webservices(koalect_webservices)(koalect_id)
                    if isinstance(koalect_output, tuple):
                        idspb = []
                        idspb = res_partner_obj.search(cr, uid, [('email', '=ilike', koalect_output[1]['user']['email'])])
                        count_partners = 0
                        if idspb and len(idspb) > 0:
                            partner = res_partner_obj.browse(cr, uid, idspb[0])
                            count_partners += 1
                        if count_partners == 1:
                            if not(partner_id):
                                partner_id = partner.id
                            if not move_line:
                                if partner.customer and not (partner.supplier):
                                    account = partner.property_account_receivable.id
                                    transaction_type = 'customer'
                                elif partner.supplier and not (partner.customer):
                                    account = partner.property_account_payable.id
                                    transaction_type = 'supplier'

                if lines2.t23_account_nbr:
                    idspb= []
                    idspb = partner_obj.search(cr, uid, [('acc_number'.replace(' ',''), '=', lines2.t23_account_nbr.replace(' ',''))])
# 		    print datetime.datetime.now() , 'partner gezocht '
                    count_partners = 0
                    if idspb and len(idspb) > 0 :
                        for p in idspb:
                            if partner_obj.browse(cr, uid, idspb[0]).partner_id.active:
                                partner = partner_obj.browse(cr, uid, idspb[0]).partner_id
                                count_partners += 1
                    if count_partners == 1:
#                    if ids and len(ids) == 1:
#                        partner = partner_obj.browse(cr, uid, ids[0], context=context).partner_id
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
                    else:
                        if structcomm_message:
                            obj_mailing_partner = self.pool.get('mailing.list.partner')
                            same_refs = obj_mailing_partner.search(cr, uid, [('reference', '=', structcomm_message)])
# 			    print datetime.datetime.now() , 'mailingpartner gezocht '
                            if same_refs:
                                partner = obj_mailing_partner.browse(cr, uid, same_refs[0]).partner_id
                                if not(partner_id):
                                    partner_id = partner.id
                                    account = partner.property_account_receivable.id
                                    transaction_type = 'customer'
# 		print datetime.datetime.now() , 'statement maken ' 
                
                if not(nbr_lines > sequence):
                    context['last_line'] = True

                if lines2.t23_account_nbr and isinstance(lines2.t23_account_nbr, str):
                    account_nbr = lines2.t23_account_nbr.replace(' ',''),
                else:
                    account_nbr = '' 

                #If account is 000000 set type as general
                acc = self.pool.get('account.account').browse(cr, uid, account)
                if acc.code == '000000':
                    transaction_type = 'general'

                journal = self.pool.get('account.journal').browse(cr, uid, journal_id)
                if journal.membership_journal:
                    transaction_type = 'general'
                    
                stat_line_id = stat_line_obj.create(cr, uid, {
                      'ref': ref,
                      'statement_id': stat_id,
                      'sequence': sequence,
                      'type': transaction_type,
                      'company_id': company_id,
                      'note': "\n".join(note),
                      'journal_id': journal_id,
                      'amount': lines2.t21_amount,
                      'date': lines2.t21_date,
                      'partner_id': partner_id,
                      'account_id': account,
                      'voucher_id': voucher_id,
                      'coda_account_number': account_nbr,
                      'transaction_code': lines2.t21_code,
                      'employee_id': None,
                      'asset_id': None,
                      'state': 'draft',
                      'structcomm_flag': lines2.t21_struct,
                      'structcomm_message': structcomm_message,
                      'name': name,
                      'name_zonder_adres': name_zonder_adres,
                      'lines2_id': lines2.id,
                      'move_flag': move_flag,
                      }, context=context)

                if isinstance(koalect_output, tuple):
                    account_coda_koalect_obj.create(cr, uid, {
                        'stat_line_id': stat_line_id,
                        'firstname': koalect_output[1]['user']['firstname'],
                        'lastname': koalect_output[1]['user']['lastname'],
                        'email': koalect_output[1]['user']['email'],
                        'street': koalect_output[1]['user']['address']['street'],
                        'number': koalect_output[1]['user']['address']['number'],
                        'box':koalect_output[1]['user']['address']['box'],
                        'city': koalect_output[1]['user']['address']['city'],
                        'postal_code': koalect_output[1]['user']['address']['postal_code'],
                        'country': koalect_output[1]['user']['address']['country'],
                        'is_tax_certificate': koalect_output[1]['is_tax_certificate'],
                        'koalect_id': koalect_output[0],
                       }, context=context)

# 		print datetime.datetime.now() , 'statement gemaakt ' 
#  if Sepa Direct Debit and payment is refused create a coda_sdd_reference record 
#                 if lines2.t21_struct:
#                     print 'type: ', lines2.t21_struct_type, ' ' , lines2.t21_struct_comm             
                    
                if lines2.t21_struct_type == '127' and lines2.t21_struct_comm[8:9] != '0':
                    sdd_struct = ''.join(filter(None, [lines2.t21_struct_comm, lines2.t22_free_comm, lines2.t23_free_comm]))
                    ids_mandate=[]
                    ids_mandate = sdd_mandate_obj.search(cr, uid,[('unique_mandate_reference', '=' , sdd_struct[44:79].rstrip())])                                    
                    id_mandate = None
                    if ids_mandate:
                        id_mandate = ids_mandate[0]
                        sdd_mandate_ids = sdd_mandate_obj.browse(cr, uid, [id_mandate])
                        for mand in sdd_mandate_ids:
                            partner_id = mand.partner_bank_id.partner_id.id
                    sdd_ref_id = sdd_ref_obj.create(cr, uid, {
                      'lines2_id': lines2.id,
                      'stat_id': stat_id,
                      'date': sdd_struct[4:6] + sdd_struct[2:4] + sdd_struct[0:2],
                      'partner_id': partner_id,
                      'sdd_mandate_id': id_mandate,
                      'type': sdd_struct[6:7],
                      'scheme': sdd_struct[7:8],
                      'pay_reason': sdd_struct[8:9],
                      'partner': sdd_struct[9:44],
                      'mandate_ref': sdd_struct[44:79],
                      'comm': sdd_struct[79:141],
                      'type_R': sdd_struct[141:142],
                      'reason': sdd_struct[142:146],
                      'name': ''.join(filter(None, lines2.t22_ref_cust)),
                      }, context=context)
                if lines2.t21_struct_type == '107' and lines2.t21_struct_comm[48:49] != '0':
                    sdd_struct = ''.join(filter(None, [lines2.t21_struct_comm, lines2.t22_free_comm, lines2.t23_free_comm]))
                    ids_mandate=[]
                    ids_mandate = sdd_mandate_obj.search(cr, uid,[('original_mandate_identification', '=' , 'DOM80' + sdd_struct[0:12])])                                    
                    id_mandate = None
                    if ids_mandate:
                        id_mandate = ids_mandate[0]
                    sdd_ref_id = sdd_ref_obj.create(cr, uid, {
                      'lines2_id': lines2.id,
                      'stat_id': stat_id,
                      'date': sdd_struct[16:18] + sdd_struct[14:16] + sdd_struct[12:14],
                      'partner_id': partner_id,
                      'sdd_mandate_id': id_mandate,
#                       'type': ,
#                       'scheme': ,
                      'pay_reason': sdd_struct[48:49],
#                       'partner': ,
                      'mandate_ref': sdd_struct[0:12],
                      'comm': sdd_struct[18:48],
#                       'type_R': ,
#                       'reason': ,
                      'name': ''.join(filter(None, lines2.t22_ref_cust)),
                      }, context=context)
                 
#                 print lines2.det2_ids
                    
                for det2 in lines2.det2_ids:
#                     if det2.t21_struct:
#                         print 'type: ', det2.t21_struct_type, ' ' , det2.t21_struct_comm             
                        
                    if det2.t21_struct_type == '127' and det2.t21_struct_comm[8:9] != '0':
                        sdd_struct = ''.join(filter(None, [det2.t21_struct_comm, det2.t22_free_comm, det2.t23_free_comm]))
                        ids_mandate=[]
                        ids_mandate = sdd_mandate_obj.search(cr, uid,[('unique_mandate_reference', '=' , sdd_struct[44:79].rstrip())])                                    
                        id_mandate = None
                        if ids_mandate:
                            id_mandate = ids_mandate[0]
                            sdd_mandate_ids = sdd_mandate_obj.browse(cr, uid, [id_mandate])
                            for mand in sdd_mandate_ids:
                                partner_id = mand.partner_bank_id.partner_id.id
                        sdd_ref_id = sdd_ref_obj.create(cr, uid, {
                          'lines2_id': det2.lines2_id.id,
                          'stat_id': stat_id,
                          'date': sdd_struct[4:6] + sdd_struct[2:4] + sdd_struct[0:2],
                          'partner_id': partner_id,
                          'sdd_mandate_id': id_mandate,
                          'type': sdd_struct[6:7],
                          'scheme': sdd_struct[7:8],
                          'pay_reason': sdd_struct[8:9],
                          'partner': sdd_struct[9:44],
                          'mandate_ref': sdd_struct[44:79],
                          'comm': sdd_struct[79:141],
                          'type_R': sdd_struct[141:142],
                          'reason': sdd_struct[142:146],
                          'name': ''.join(filter(None, det2.t22_ref_cust)),
                          }, context=context)
                    if det2.t21_struct_type == '107' and det2.t21_struct_comm[48:49] != '0':
                        sdd_struct = ''.join(filter(None, [det2.t21_struct_comm, det2.t22_free_comm, det2.t23_free_comm]))
                        ids_mandate=[]
                        ids_mandate = sdd_mandate_obj.search(cr, uid,[('original_mandate_identification', '=' , 'DOM80' + sdd_struct[0:12])])                                    
                        id_mandate = None
                        if ids_mandate:
                            id_mandate = ids_mandate[0]
                        sdd_ref_id = sdd_ref_obj.create(cr, uid, {
                          'lines2_id': det2.lines2_id.id,
                          'stat_id': stat_id,
                          'date': sdd_struct[16:18] + sdd_struct[14:16] + sdd_struct[12:14],
                          'partner_id': partner_id,
                          'sdd_mandate_id': id_mandate,
    #                       'type': ,
    #                       'scheme': ,
                          'pay_reason': sdd_struct[48:49],
    #                       'partner': ,
                          'mandate_ref': sdd_struct[0:12],
                          'comm': sdd_struct[18:48],
    #                       'type_R': ,
    #                       'reason': ,
                          'name': ''.join(filter(None, det2.t22_ref_cust)),
                          }, context=context)
                    
                    
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

class account_move_line(osv.osv):
    _inherit = 'account.move.line' 
    _columns = {
        'ref': fields.char('Reference', size=64),
               }
account_move_line()


class account_journal(osv.osv):

    _inherit = 'account.journal'

    _columns = {
            'membership_journal': fields.boolean('Lidmaatschappen Journaal'),
    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:# -*- coding: utf-8 -*-

