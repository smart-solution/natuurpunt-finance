# -*- coding: utf-8 -*-
{
    "name" : "natuurpunt_account_project_manager",
    "version" : "1.0",
    "author" : "Natuurpunt (mattias.vanopstal@natuurpunt.be)",
    "website" : "www.natuurpunt.be",
    "category" : "Generic Modules/Finance",
    "description": """Accounting for project managers""",    
    "update_xml" : ['natuurpunt_account_pm_view.xml',],
    "depends" : ["account_budget_detailline","multi_analytical_account",],
    "data" : ['security/ir.model.access.csv',],
    "active": False,
    "installable": True
}
