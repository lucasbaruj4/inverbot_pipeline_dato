# Aca se guardan los links a las páginas que Inverbot va a crawlear.
from crewai_tools import (
    # SerperDevTool,
    FirecrawlScrapeWebsiteTool,
    FirecrawlCrawlWebsiteTool
)
# def listado_emisores_tool():
#     listado_emisores_tool = FirecrawlCrawlWebsiteTool(url='https://www.bolsadevalores.com.py/listado-de-emisores/', extractor_options={'extractionPrompt':'Página de listado de emisores de la BVA, contiene un listado de emisores, cuando se selecciona un emisor en específico, se pueden encontrar balances, prospectos, análisis de riesgo y hechos relevantes del emisor en cuestión.'})
#     return listado_emisores_tool
# def informes_diarios_tool():
#     informes_diarios_tool = FirecrawlScrapeWebsiteTool(url='https://www.bolsadevalores.com.py/informes-diarios/', extractor_options={'extractionPrompt':'Informes diarios de la BVA con movimientos del mercado. Extraer todos los datos de la tabla'})
#     return informes_diarios_tool
# def informes_mensuales_tool():
#     informes_mensuales_tool = FirecrawlCrawlWebsiteTool(url='https://www.bolsadevalores.com.py/informes-mensuales/', extractor_options={'extractionPrompt':'Informes mensuales de la BVA, incluyendo PDFs y datos estructurados.'})
#     return informes_mensuales_tool
# def informes_anuales_tool():
#     informes_anuales_tool = FirecrawlCrawlWebsiteTool(url='https://www.bolsadevalores.com.py/informes-anuales/', extractor_options={'extractionPrompt':'Informes anuales de la BVA en formato PDF.'})
#     return informes_anuales_tool
# def datos_gov_tool():
#     datos_gov_tool = FirecrawlCrawlWebsiteTool(url='https://www.datos.gov.py/', extractor_options={'extractionPrompt':'Portal oficial de datos abiertos de Paraguay que incluye datos macroeconómicos del BCP y otras instituciones.'})
#     return datos_gov_tool
# def ine_tool():
#     ine_tool = FirecrawlCrawlWebsiteTool(url='https://www.ine.gov.py/', extractor_options={'extractionPrompt':'Instituto Nacional de Estadística con datasets que contienen datos macroeconómicos y estadísticas oficiales.'})
#     return ine_tool
# def ine_portal_tool():
#     ine_portal_tool = FirecrawlCrawlWebsiteTool(url='https://www.ine.gov.py/vt/publicacion.php/', extractor_options={'extractionPrompt':'Portal del Instituto Nacional de Estadística (INE) para publicaciones y datos sociales.'})
#     return ine_portal_tool
# def contratos_publicos_tool():
#     contratos_publicos_tool = FirecrawlCrawlWebsiteTool(url='https://www.contrataciones.gov.py/', extractor_options={'extractionPrompt':'Portal de la Dirección Nacional de Contrataciones Públicas (DNCP) para datos de licitaciones y contratos.'})
#     return contratos_publicos_tool
# def dnit_tool():
#     dnit_tool = FirecrawlCrawlWebsiteTool(url='https://www.dnit.gov.py/web/portal-institucional/invertir-en-py', extractor_options={'extractionPrompt':'Sección del portal del DNIT con información para invertir en Paraguay.'})
#     return dnit_tool
# def dnit_informes_tool():
#     dnit_informes_tool=FirecrawlCrawlWebsiteTool(url='https://www.dnit.gov.py/web/portal-institucional/informes-financieros', extractor_options={'extractionPrompt':'Sección del portal del DNIT con informes financieros, en la parte de abajo hay un boton de paginacion, usalos una vez que hayas scrapeado todos los datos de una pagina'})
#     return dnit_informes_tool

    
    
    
# 'sources_list':[
    # 'https://www.bolsadevalores.com.py/listado-de-emisores/',
    # 'https://www.bolsadevalores.com.py/informes-diarios/',
    # 'https://www.bolsadevalores.com.py/informes-mensuales/',
    # 'https://www.bolsadevalores.com.py/informes-anuales/',
    # 'https://www.datos.gov.py/',
    # (hay que encontrar una forma de sacar datos del BCP)',
    # 'https://www.ine.gov.py/',
    # 'https://www.ine.gov.py/vt/publicacion.php/',
    # 'https://www.contrataciones.gov.py/',
    # 'https://www.dnit.gov.py/web/portal-institucional/invertir-en-py',
    # 'https://www.dnit.gov.py/web/portal-institucional/informes-financieros' ] 
