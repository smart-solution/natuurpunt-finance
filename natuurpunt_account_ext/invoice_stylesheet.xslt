<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.1"
xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionBasicComponents-2">

<xsl:param
  name="xmldata"/>

<xsl:variable
  name="root"
  select="document($xmldata)/root"/>

<xsl:variable
  name="Invoice"
  select="document($xmldata)/root/Invoice"/>

<xsl:template match="node()|@*">
    <xsl:copy>
        <xsl:apply-templates select="node()|@*"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="node()|@*" mode="clone">
    <xsl:param name="i"/>
    <xsl:param name="nodeOffset"/>

    <xsl:copy>
        <xsl:apply-templates select="node()|@*" mode="clone">
            <xsl:with-param name="i" select="$i"/>
            <xsl:with-param name="nodeOffset" select="$nodeOffset"/>
        </xsl:apply-templates>
    </xsl:copy>
</xsl:template>

<xsl:template match="cac:TaxSubtotal">
    <xsl:variable name="TaxSubtotalTemplateNode" select="."/>

    <xsl:call-template name="clone">
        <xsl:with-param name="maxCount" select="count($root/TaxSubtotal)"/>
        <xsl:with-param name="nodeToCopy" select="$TaxSubtotalTemplateNode"/>
        <xsl:with-param name="nodeOffset" select="2"/>
    </xsl:call-template>

</xsl:template>

<xsl:template match="cac:InvoiceLine">
    <xsl:variable name="InvoiceLineTemplateNode" select="."/>

    <xsl:call-template name="clone">
        <xsl:with-param name="maxCount" select="count($root/InvoiceLine)"/>
        <xsl:with-param name="nodeToCopy" select="$InvoiceLineTemplateNode" />
    </xsl:call-template>

</xsl:template>

<xsl:template match="text()[starts-with(.,'$')]">
        <xsl:variable name="element" select="substring(.,2)"/>
        <xsl:variable name="toplevel" select="ancestor::*[last()-1]"/>
        <xsl:variable name="lookup" select="$Invoice/*[name() = local-name($toplevel)]"/>
        <xsl:choose>
            <xsl:when test="$lookup and count(ancestor::*) &gt; 2">
               <xsl:value-of select="$lookup/*[name() = $element]"/>
            </xsl:when>
            <xsl:otherwise>
               <xsl:value-of select="$Invoice/*[name() = $element]"/>
            </xsl:otherwise>
        </xsl:choose>
</xsl:template>

<xsl:template match="text()[starts-with(.,'$')]" mode="clone">
        <xsl:param name="i" select="0"/>
        <xsl:param name="nodeOffset" select="1"/>
        <xsl:variable name="element" select="substring(.,2)"/>
        <xsl:variable name="toplevel" select="ancestor::*[last()-$nodeOffset]"/>
        <xsl:variable name="lookup" select="$root/*[name() = local-name($toplevel)][$i]"/>
        <xsl:value-of select="$lookup/*[name() = $element]"/>
</xsl:template>

<xsl:template name="clone">
   <xsl:param name="nodeToCopy"/>
   <xsl:param name="maxCount"/>
   <xsl:param name="i" select="1"/>
   <xsl:param name="nodeOffset" select="1"/>

   <xsl:choose>
       <xsl:when test="$i &lt;= $maxCount">
           <xsl:element name="{name($nodeToCopy)}">
                <xsl:apply-templates select="$nodeToCopy/child::*" mode="clone">
                    <xsl:with-param name="i" select="$i"/>
                    <xsl:with-param name="nodeOffset" select="$nodeOffset"/>
                </xsl:apply-templates>
           </xsl:element>

           <xsl:call-template name="clone">
               <xsl:with-param name="maxCount" select="$maxCount" />
               <xsl:with-param name="nodeToCopy" select="$nodeToCopy" />
               <xsl:with-param name="i" select="$i+1" />
               <xsl:with-param name="nodeOffset" select="$nodeOffset"/>
           </xsl:call-template>
        </xsl:when>
       <xsl:otherwise />
   </xsl:choose>
</xsl:template>

</xsl:stylesheet>
