#!/usr/bin/env python
# -*- encoding: utf-8 -*-
##############################################################################
#
#
##############################################################################
{
    "name" : "Account Sale Invoice Customer Account",
    "version" : "1.0",
    "author" : "SmartSolution",
    "category" : "Generic Modules/Base",
    "description": """
""",
    "depends" : ["account"],
    "init_xml" : [
        ],
    "update_xml" : [
        'account_sale_invoice_customer_account_view.xml',
#        'security/ir.model.access.csv'
        ],
    "active": False,
    "installable": True
}
