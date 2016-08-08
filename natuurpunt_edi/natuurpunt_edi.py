# -*- encoding: utf-8 -*-

from osv import fields, osv
from openerp.tools.translate import _

class res_edi_xml(osv.osv):
    _name = 'res.edi.xml'

    _columns = {
        'document_type':fields.selection([('out_invoice','Out Invoice'), ('out_refund','Out Refund')],'DocumentType'),
        'name': fields.char('Omschrijving'),
        'xml': fields.text('xml template', translate=False, help="xml edi template"),
        'xslt': fields.text('xslt stylesheet', translate=False, help="xslt stylesheet"),
    }

res_edi_xml()

class res_partner(osv.osv):
    _inherit = 'res.partner'

    _columns = {
        'edi_xml_ids': fields.many2many('res.edi.xml', 'res_edi_xml_rel_rel', 'partner_id', 'edi_xml_id', 'EDI xml'),
    }

res_partner()

