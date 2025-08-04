# CLAUDE.md - InverBot Project Context
## IMPORTANT: 
1. **ALWAYS** make sure to save all user prompts and actions taken in a file named "CHATLOG.md" inside the claude folder (create file if not found) to facilitate different Coding Agents quick context understanding.
2. **ALWAYS** plan your tasks first before executing anything, manage task's status, task's dependencies on other tasks and task descriptions in a filed named "TASKS.md" inside the claude folder (create file if not found).
3. **ALWAYS** read CHATLOG.md, CLAUDE.md, and TASKS.md before starting work, these are your "context files"
4. **ALWAYS** update your context files after completing significant work 
5. **Follow existing code patterns** and architectural decisions documented here
6. **Use established terminology** and maintain consistent documentation style
7. **Mark task status** using: ✅ (complete), 🔄 (in progress), ⏳ (pending)
8. **CRITICAL**: Make all features **easily verifiable by a human** - include clear instructions for testing functionality
9. **ALWAYS** identify yourself with your model name and date you're working on the project on before interacting with CLAUDE.md, TASKS.md or CHATLOG.md 
10. **NEVER overwrite or modify content written by other agents** - Only append new sections or update your own previous work to preserve collaboration history



## Proyecto Overview

### InverBot - Sistema ETL Financiero Paraguay
Sistema de extracción, procesamiento y carga de datos financieros paraguayos usando CrewAI, con almacenamiento híbrido en Supabase (datos estructurados) y Pinecone (vectores), el objetivo es crear esta base de datos para facilitar un sistema RAG.

### Arquitectura General
```
Extractor → Processor → Vector → Loader
    ↓         ↓         ↓        ↓
Firecrawl → Normaliza → PDFs → Supabase
          → Valida   → Chunks → Pinecone
          → Relaciona → Embeddings
```

## Bases de Datos

### Supabase - Estructura Completa (14 Tablas)

#### Tablas Maestras
1. **Categoria_Emisor**
   - `id_categoria_emisor: INT (PK)`
   - `categoria_emisor: VARCHAR(100)`

2. **Emisores**
   - `id_emisor: INT (PK)`
   - `nombre_emisor: VARCHAR(250)`
   - `id_categoria_emisor: INT (FK)`
   - `calificacion_bva: VARCHAR(100)`

3. **Moneda**
   - `id_moneda: INT (PK)`
   - `codigo_moneda: VARCHAR(10)`
   - `nombre_moneda: VARCHAR(50)`

4. **Frecuencia**
   - `id_frecuencia: INT (PK)`
   - `nombre_frecuencia: VARCHAR(50)`

5. **Tipo_Informe**
   - `id_tipo_informe: INT (PK)`
   - `nombre_tipo_informe: VARCHAR(100)`

6. **Periodo_Informe**
   - `id_periodo: INT (PK)`
   - `nombre_periodo: VARCHAR(50)`

7. **Unidad_Medida**
   - `id_unidad_medida: INT (PK)`
   - `simbolo: VARCHAR(10)`
   - `nombre_unidad: VARCHAR(50)`

8. **Instrumento**
   - `id_instrumento: INT (PK)`
   - `simbolo_instrumento: VARCHAR(50)`
   - `nombre_instrumento: VARCHAR(255)`

#### Tablas Principales
9. **Informe_General**
   - `id_informe: INT (PK)`
   - `id_emisor: INT (FK, NULLABLE)`
   - `id_tipo_informe: INT (FK)`
   - `id_frecuencia: INT (FK, NULLABLE)`
   - `id_periodo: INT (FK, NULLABLE)`
   - `titulo_informe: VARCHAR(500)`
   - `resumen_informe: TEXT (NULLABLE)`
   - `fecha_publicacion: DATE`
   - `url_descarga_original: VARCHAR(500) (NULLABLE)`
   - `detalles_informe_jsonb: JSONB (NULLABLE)`

10. **Resumen_Informe_Financiero**
    - `id_resumen_financiero: INT (PK)`
    - `id_informe: INT (FK)`
    - `id_emisor: INT (FK)`
    - `fecha_corte_informe: DATE`
    - `moneda_informe: INT (FK)`
    - `activos_totales: DECIMAL (NULLABLE)`
    - `pasivos_totales: DECIMAL (NULLABLE)`
    - `patrimonio_neto: DECIMAL (NULLABLE)`
    - `disponible: DECIMAL (NULLABLE)`
    - `utilidad_del_ejercicio: DECIMAL (NULLABLE)`
    - `ingresos_totales: DECIMAL (NULLABLE)`
    - `costos_operacionales: DECIMAL (NULLABLE)`
    - `total_ganancias: DECIMAL (NULLABLE)`
    - `total_perdidas: DECIMAL (NULLABLE)`
    - `retorno_sobre_patrimonio: DECIMAL (NULLABLE)`
    - `calificacion_riesgo_tendencia: VARCHAR(100) (NULLABLE)`
    - `utilidad_neta_por_accion_ordinaria: DECIMAL (NULLABLE)`
    - `deuda_total: DECIMAL (NULLABLE)`
    - `ebitda: DECIMAL (NULLABLE)`
    - `margen_neto: DECIMAL (NULLABLE)`
    - `flujo_caja_operativo: DECIMAL (NULLABLE)`
    - `capital_integrado: DECIMAL (NULLABLE)`
    - `otras_metricas_jsonb: JSONB (NULLABLE)`

11. **Dato_Macroeconomico**
    - `id_dato_macro: INT (PK)`
    - `id_informe: INT (FK, NULLABLE)`
    - `indicador_nombre: VARCHAR(250)`
    - `fecha_dato: DATE`
    - `valor_numerico: DECIMAL`
    - `unidad_medida: INT (FK, NULLABLE)`
    - `id_frecuencia: INT (FK)`
    - `link_fuente_especifico: VARCHAR(500) (NULLABLE)`
    - `otras_propiedades_jsonb: JSONB (NULLABLE)`
    - `id_moneda: INT (FK, NULLABLE)`
    - `id_emisor: INT (FK, NULLABLE)`

12. **Movimiento_Diario_Bolsa**
    - `id_operacion: INT (PK)`
    - `fecha_operacion: DATE`
    - `cantidad_operacion: DECIMAL`
    - `id_instrumento: INT (FK)`
    - `id_emisor: INT (FK)`
    - `fecha_vencimiento_instrumento: DATE (NULLABLE)`
    - `id_moneda: INT (FK)`
    - `precio_operacion: DECIMAL`
    - `precio_anterior_instrumento: DECIMAL (NULLABLE)`
    - `tasa_interes_nominal: DECIMAL (NULLABLE)`
    - `tipo_cambio: DECIMAL (NULLABLE)`
    - `variacion_operacion: DECIMAL (NULLABLE)`
    - `volumen_gs_operacion: DECIMAL (NULLABLE)`

13. **Licitacion_Contrato**
    - `id_licitacion_contrato: INT (PK)`
    - `id_emisor_adjudicado: INT (FK, NULLABLE)`
    - `titulo: VARCHAR(500)`
    - `entidad_convocante: VARCHAR(255) (NULLABLE)`
    - `monto_adjudicado: DECIMAL (NULLABLE)`
    - `id_moneda: INT (FK, NULLABLE)`
    - `fecha_adjudicacion: DATE (NULLABLE)`

### Pinecone - Estructura Vectorial

#### Configuración Común
- **Dimensiones**: 768 (Gemini embedding-001)
- **Métrica**: cosine
- **Capacidad**: Serverless
- **Proveedor**: AWS
- **Región**: us-east-1

#### Índices (4)
1. **documentos-informes-vector**
   - Embeddings de informes completos, estudios, documentos extensos
   - Metadatos:
     - `id_informe, id_emisor, id_tipo_informe, id_frecuencia, id_periodo, fecha_publicacion, chunk_id, chunk_text`

2. **dato-macroeconomico-vector**
   - Embeddings de texto contextual alrededor de datos macroeconómicos
   - Metadatos:
     - `id_dato_macro, indicador_nombre, fecha_dato, id_unidad_medida, id_moneda, id_frecuencia, id_emisor, id_informe, chunk_id, chunk_text`

3. **licitacion-contrato-vector**
   - Embeddings de información detallada sobre licitaciones y contratos
   - Metadatos:
     - `id_licitacion_contrato, titulo, id_emisor_adjudicado, entidad_convocante, monto_adjudicado, id_moneda, fecha_adjudicacion, chunk_id, chunk_text`

## Fuentes de Datos Paraguayas

### 1. BVA (Bolsa de Valores de Asunción)
- **Balances de Empresas**: https://www.bolsadevalores.com.py/listado-de-emisores/
- **Movimientos Diarios**: https://www.bolsadevalores.com.py/informes-diarios/
- **Volumen Mensual**: https://www.bolsadevalores.com.py/informes-mensuales/
- **Resumen Anual**: https://www.bolsadevalores.com.py/informes-anuales/

### 2. Datos Gubernamentales
- **Portal Datos Abiertos**: https://www.datos.gov.py/
- **INE Principal**: https://www.ine.gov.py/
- **INE Publicaciones**: https://www.ine.gov.py/vt/publicacion.php/

### 3. Contrataciones y Finanzas
- **DNCP**: https://www.contrataciones.gov.py/
- **DNIT Inversión**: https://www.dnit.gov.py/web/portal-institucional/invertir-en-py
- **DNIT Financiero**: https://www.dnit.gov.py/web/portal-institucional/informes-financieros

### 4. Contexto Macroeconómico
- **MIC, MEF, BCP**: https://www.bcp.gov.py/
- **DGEEC**: Estadísticas sociales y demográficas

## Agentes CrewAI

### 1. Extractor Agent
**Status**: ✅ **COMPLETO**
- 10 scrapers específicos implementados
- Cada scraper usa firecrawl internamente
- Cubre todas las fuentes paraguayas

### 2. Processor Agent  
**Status**: ❌ **INCOMPLETO (1/5 tools)**

**Tools Implementadas:**
- ✅ `filter_duplicate_data` - Controla duplicados en Supabase

**Tools FALTANTES:**
- ❌ `normalize_data` - Limpiar y estandarizar datos extraídos
- ❌ `validate_data` - Verificar conformidad con esquemas
- ❌ `create_entity_relationships` - Establecer relaciones FK
- ❌ `structure_extracted_data` - Organizar datos en formato normalizado

### 3. Vector Agent
**Status**: ❌ **INCOMPLETO (1/4 tools)**

**Tools Implementadas:**
- ✅ `filter_duplicate_vectors` - Controla duplicados en Pinecone

**Tools FALTANTES:**
- ❌ `extract_text_from_pdf` - Extraer texto de documentos PDF
- ❌ `chunk_document` - Dividir texto en fragmentos con solapamiento
- ❌ `prepare_document_metadata` - Crear metadatos para vectores

### 4. Loader Agent
**Status**: ✅ **COMPLETO**
- ✅ `load_data_to_supabase` - Carga datos estructurados
- ✅ `load_vectors_to_pinecone` - Crea embeddings y carga vectores
- ✅ `check_loading_status` - Verifica estado de carga
- ✅ `validate_data_before_loading` - Validación previa

## Configuración Técnica

### Variables de Entorno Requeridas
```bash
SUPABASE_URL="tu_supabase_url"
SUPABASE_KEY="tu_supabase_key"
PINECONE_API_KEY="tu_pinecone_key"
GEMINI_API_KEY="tu_gemini_key"
FIRECRAWL_API_KEY="tu_firecrawl_key"
```

### Embeddings - Gemini
- **Modelo**: `models/embedding-001`
- **Dimensiones**: 768
- **Task Type**: `retrieval_document`
- **Configuración**:
  ```python
  import google.generativeai as genai
  genai.configure(api_key=gemini_api_key)
  response = genai.embed_content(
      model="models/embedding-001",
      content=text,
      task_type="retrieval_document"
  )
  ```

### Campos Únicos para Control de Duplicados

#### Supabase
```python
table_unique_fields = {
    "Categoria_Emisor": ["categoria_emisor"],
    "Emisores": ["nombre_emisor"],
    "Moneda": ["codigo_moneda"],
    "Frecuencia": ["nombre_frecuencia"],
    "Tipo_Informe": ["nombre_tipo_informe"],
    "Periodo_Informe": ["nombre_periodo"],
    "Unidad_Medida": ["simbolo"],
    "Instrumento": ["simbolo_instrumento"],
    "Informe_General": ["titulo_informe", "fecha_publicacion"],
    "Resumen_Informe_Financiero": ["id_informe", "fecha_corte_informe"],
    "Dato_Macroeconomico": ["indicador_nombre", "fecha_dato", "id_emisor"],
    "Movimiento_Diario_Bolsa": ["fecha_operacion", "id_instrumento", "id_emisor"],
    "Licitacion_Contrato": ["titulo", "fecha_adjudicacion"]
}
```

#### Pinecone
```python
unique_field_mapping = {
    "documentos-informes-vector": ["id_informe", "chunk_id"],
    "dato-macroeconomico-vector": ["id_dato_macro", "chunk_id"],
    "licitacion-contrato-vector": ["id_licitacion_contrato", "chunk_id"]
}
```

## Bugs Críticos Corregidos

### 1. Supabase Client (filter_duplicate_data)
```python
# ❌ INCORRECTO:
supabase = create_client(supabase_url, supabase_url)

# ✅ CORRECTO:
supabase = create_client(supabase_url, supabase_key)
```

### 2. Pinecone API (filter_duplicate_vectors)
```python
# ❌ API Antigua:
pinecone.init(api_key=api_key, environment=environment)

# ✅ Nueva API:
from pinecone import Pinecone
pc = Pinecone(api_key=pinecone_api_key)
```

### 3. Embeddings
- Cambiado de OpenAI a Gemini
- Configuración completa implementada

## Próximos Pasos CRÍTICOS

### Implementar 7 Tools Faltantes

**Processor Agent (4 tools):**
1. `normalize_data` - Procesar datos crudos de scrapers
2. `validate_data` - Validar esquemas antes de insertar
3. `create_entity_relationships` - Establecer FKs correctas
4. `structure_extracted_data` - Formato final para carga

**Vector Agent (3 tools):**
1. `extract_text_from_pdf` - Muchos informes son PDFs
2. `chunk_document` - Dividir textos largos para vectorización
3. `prepare_document_metadata` - Metadatos correctos para Pinecone

### Consideraciones de Implementación

**Chunking Strategy:**
- Tamaño: 1000-1500 tokens
- Overlap: 200-300 tokens
- Mantener contexto semántico

**PDF Processing:**
- Usar PyMuPDF o similar
- Extraer texto + metadatos
- Manejar imágenes con OCR si necesario

**Entity Relationships:**
- Resolver nombres a IDs
- Crear entidades maestras primero
- Validar integridad referencial

## Test Mode
- Variable global: `test_mode = True`
- Limita extracción para desarrollo
- Cambiar a `False` para producción

## Estado Actual del Pipeline
```
Extractor (10/10) ✅ → Processor (1/5) ❌ → Vector (1/4) ❌ → Loader (4/4) ✅
```

**Sin las 7 tools faltantes, el pipeline está roto** - los datos se extraen pero no se procesan correctamente antes de la carga.

## Notas de Desarrollo
- Batch sizes optimizados: 50 para Supabase, 20 para Pinecone
- Manejo robusto de errores implementado
- Validación previa antes de carga
- Reportes detallados de operaciones
- Control granular de duplicados por tabla/índice

