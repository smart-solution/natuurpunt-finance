#!/usr/bin/python
# _*_ encoding: utf-8 _*_

import xmlrpclib

server = 'localhost'
username = 'admin' #the user
pwd = 'n2aevl8w'      #the password of the user
dbname = 'natuurpunt'    #the database

# Get the uid
sock_common = xmlrpclib.ServerProxy ('http://%s:8069/xmlrpc/common'%(server))
uid = sock_common.login(dbname, username, pwd)

#replace localhost with the address of the server
sock = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))


# Add the 3 dimensions to the 6x and 7x accounts of Lava
# 1. Get ids of the accounts


## To clean up: delete from account_account_analytic_dimension where account_id in (select id from account_account where (code like '6%' or code ilike '7%') and type != 'view' and company_id = 8);

acc_ids = sock.execute(dbname, uid, pwd, 'account.account', 'search', ['|',('code','ilike','6%'),('code','ilike','7%'),('type','!=','view'),('company_id','=',8)])
print "acc_ids:",acc_ids
print "Nbr accs:",len(acc_ids)

results = []
for acc in acc_ids:
    data = {
	'analytic_account_required': True,
	'dimension_id': 17,
	'account_id': acc,
    }
    results.append(sock.execute(dbname, uid, pwd, 'account.account.analytic.dimension', 'create', data))

for acc in acc_ids:
    data = {
	'analytic_account_required': False,
	'dimension_id': 18,
	'account_id': acc,
    }
    results.append(sock.execute(dbname, uid, pwd, 'account.account.analytic.dimension', 'create', data))

for acc in acc_ids:
    data = {
	'analytic_account_required': False,
	'dimension_id': 16,
	'account_id': acc,
    }
    results.append(sock.execute(dbname, uid, pwd, 'account.account.analytic.dimension', 'create', data))

print "IDS:",results





"""
for i_id in i_ids:

    i_fields =  ['currency_id', 'partner_id', 'residual', 'name', 'type', 'amount_total','move_id', 'date_invoice']

    i_data = sock.execute(dbname, uid, pwd, 'account.invoice', 'read', i_id, i_fields)

    print 'i_data:',i_data

    v_data = {

            'comment': 'Payment',

            'payment_rate_currency_id':i_data['currency_id'][0],

            'partner_id':i_data['partner_id'][0],

            'amount':i_data['amount_total'],

            'number':i_data['name'],

            'invoice_type':i_data['type'],

            'type': 'receipt',

            'payment_option': 'without_writeoff',

            'payment_rate': 1,

            'journal_id': 9,

            'period_id': 7,

            'account_id': 907,

            'company_id': 1,

#            'move_id': i_data['move_id'][0],

            'date': i_data['date_invoice'],

    }

    print "V_DATA:",v_data

    v_res = sock.execute(dbname, uid, pwd, 'account.voucher', 'create', v_data)

    print "V_RES:",v_res



    v_res_oc = sock.execute(dbname, uid, pwd, 'account.voucher', 'onchange_journal', [v_res], 9, [],

        False, v_data['partner_id'], v_data['date'],  v_data['amount'], v_data['type'], v_data['company_id'])

    print "V_RES_OC:",v_res_oc



    for v_line in v_res_oc['value']['line_cr_ids']:

        print "V_LINE:",v_line

        v_line['voucher_id'] = v_res

        v_line_res = sock.execute(dbname, uid, pwd, 'account.voucher.line', 'create', v_line)



    #v_res2 = sock.execute(dbname, uid, pwd, 'account.voucher', 'button_proforma_voucher', v_res)

    results = sock.exec_workflow (dbname, uid, pwd, 'account.voucher', 'proforma_voucher', v_res)
"""
