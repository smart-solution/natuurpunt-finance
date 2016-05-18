# -*- coding: utf-8 -*-
import xmlrpclib

server='xxx.natuurpunt.be'
dbname='natuurpunt'
uid=1
pwd='xxx'

#replace localhost with the address of the server
sock = xmlrpclib.ServerProxy('http://%s:8069/xmlrpc/object'%(server))

def leesfile():
  with open('/tmp/moves.csv') as f:
    res = [int(x.replace("\n", "").replace("\r","")) for x in f]
  return res

for move_id in leesfile():

   move_line_ids = sock.execute(dbname, uid, pwd, 'account.move.line', 'search', [('move_id','=',move_id)])
   print "move_id:", move_id, move_line_ids

   for mline_id in move_line_ids:

        mline = sock.execute(dbname, uid, pwd, 'account.move.line', 'read', mline_id,
                ['name','date','analytic_dimension_1_id','analytic_dimension_2_id','analytic_dimension_3_id','debit','credit','amount_currency','move_id','product_id','quantity','account_id','id','journal_id','create_uid'])

        print "MLINE:",mline

        if not mline:
            continue

        if mline['debit']:
            amount = -mline['debit']
        elif mline['credit']:
            amount = mline['credit']
        else:
            continue

        aj  = sock.execute(dbname, uid, pwd, 'account.journal', 'read', mline['journal_id'][0],['analytic_journal_id'])
        move  = sock.execute(dbname, uid, pwd, 'account.move', 'read', mline['move_id'][0],['name','period_id'])

        if mline['analytic_dimension_1_id']:
            analytic_line = {
                'name': mline['name'],
                'date': mline['date'],
                'account_id': mline['analytic_dimension_1_id'][0],
                'journal_id': aj['analytic_journal_id'] and aj['analytic_journal_id'][0] or False,
                'amount': amount,
                'amount_currency': mline['amount_currency'],
                'ref': move['name'],
                'product_id': mline['product_id'] and mline['product_id'][0] or False,
                'unit_amount': mline['quantity'],
                'general_account_id': mline['account_id'] and mline['account_id'][0] or False,
                'move_id': mline['id'],
                'user_id': 1,
                'period_id': move['period_id'][0]
            }

            aline_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', analytic_line) 

            
        if mline['analytic_dimension_2_id']:
            analytic_line = {
                'name': mline['name'],
                'date': mline['date'],
                'account_id': mline['analytic_dimension_2_id'][0],
                'journal_id': aj['analytic_journal_id'] and aj['analytic_journal_id'][0] or False,
                'amount': amount,
                'amount_currency': mline['amount_currency'],
                'ref': move['name'],
                'product_id': mline['product_id'] and mline['product_id'][0] or False,
                'unit_amount': mline['quantity'],
                'general_account_id': mline['account_id'] and mline['account_id'][0] or False,
                'move_id': mline['id'],
                'user_id': 1,
                'period_id': move['period_id'][0]
            }

            aline_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', analytic_line) 

        if mline['analytic_dimension_3_id']:
            analytic_line = {
                'name': mline['name'],
                'date': mline['date'],
                'account_id': mline['analytic_dimension_3_id'][0],
                'journal_id': aj['analytic_journal_id'] and aj['analytic_journal_id'][0] or False,
                'amount': amount,
                'amount_currency': mline['amount_currency'],
                'ref': move['name'],
                'product_id': mline['product_id'] and mline['product_id'][0] or False,
                'unit_amount': mline['quantity'],
                'general_account_id': mline['account_id'] and mline['account_id'][0] or False,
                'move_id': mline['id'],
                'user_id': 1,
                'period_id': move['period_id'][0]
            }

            aline_id = sock.execute(dbname, uid, pwd, 'account.analytic.line', 'create', analytic_line) 
