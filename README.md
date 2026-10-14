# Mercado Libre ETL

Proyecto en Python para capturar productos del catálogo de Mercado Libre en Argentina y persistir las respuestas de búsqueda y sus detalles en SQLite. El término configurado es `smartphone Samsung Galaxy A16 5g`, el dominio es `MLA-CELLPHONES` y el límite predeterminado es de 100 resultados, en páginas de hasta 50.

> **Estado de la entrega: captura de catálogo implementada; análisis de publicaciones pendiente.** El flujo actual consulta `/products/search`, guarda las páginas en `bronze_products`, reúne en memoria los IDs de catálogo encontrados, consulta `/products/{product_id}` para obtener sus detalles y hace upsert en `bronze_product_details`. No extrae el inventario completo de publicaciones de vendedores ni calcula las cinco métricas solicitadas por el desafío.

## 1. Objetivo del desafío

El enunciado original pide analizar publicaciones nuevas de smartphones Samsung Galaxy en Argentina y responder:

1. ¿Hay vendedores con múltiples publicaciones? ¿Cuántas tiene cada uno?
2. ¿Cuál es el promedio de ventas por vendedor?
3. ¿Cuál es el precio promedio en dólares?
4. ¿Qué porcentaje de artículos tiene garantía?
5. ¿Qué métodos de envío se ofrecen?

También solicita paginación de 50 registros, posibilidad de limitar la extracción, persistencia en una base de datos, un campo `JOB_RUN` con la fecha y hora de la ejecución en todas las tablas, configuración externa, credenciales fuera del código, DDL del esquema y consultas SQL para responder cada pregunta.

## 2. Alcance real de esta entrega

### Implementado en el flujo de captura de catálogo

- Lectura de credenciales desde el archivo `.env`.
- Uso del access token y renovación mediante el refresh token cuando el token necesita renovarse.
- Consultas HTTP mediante `httpx`, con encabezado Bearer, timeout y validación de errores HTTP mediante `raise_for_status()`.
- Búsqueda paginada de productos de catálogo mediante `/products/search`, con `limit`, `offset` y un máximo configurable de resultados.
- Persistencia de cada página de búsqueda como JSON en `bronze_products`.
- Deduplicación en memoria de los IDs de catálogo encontrados en la ejecución.
- Consulta de detalles mediante `/products/{product_id}`.
- Upsert de los detalles en `bronze_product_details`, usando `id` como clave primaria lógica de la tabla.
- Creación de tablas y migraciones aditivas de columnas que falten en las tablas administradas por el código.
- Cierre del engine SQLite en un bloque `finally` al salir de `main()`.

La búsqueda de detalles de catálogo se completó como continuación útil del trabajo de extracción: permite conservar y consultar los datos de los productos encontrados, aunque no sustituye la captura de publicaciones comerciales necesaria para responder las preguntas de negocio.

### No entregado

- Extracción completa y validada de publicaciones de vendedores.
- Modelo analítico normalizado para vendedor, precio, moneda, ventas, garantía y envío.
- Captura y validación de la tasa de conversión a USD.
- Consultas SQL validadas para las cinco preguntas de negocio.
- Resultados numéricos sustentados por un conjunto completo de publicaciones.

Por tanto, el ETL implementado debe entenderse como un **flujo de captura de catálogo**, no como una solución analítica completa del desafío.

## 3. Estructura del repositorio

```text
.
├── README.md
├── pyproject.toml
└── src/
    ├── api.py                 # Cliente HTTP, OAuth y paginación
    ├── config.py              # Parámetros, rutas y gestión de credenciales
    ├── data_management.py     # SQLAlchemy, SQLite, creación de tablas y upsert
    ├── data_modeling.py       # Modelos de respuestas, catálogo y credenciales
    ├── main.py                # Orquestación de la captura de catálogo
    └── transformations.py     # Extracción y validación inicial de IDs de catálogo
```

## 4. Instalación y ejecución

### Requisitos

- Python 3.12 o superior.
- [`uv`](https://docs.astral.sh/uv/).
- Credenciales válidas de una aplicación de Mercado Libre con un refresh token vigente.

Desde la raíz del repositorio, instala las dependencias:

```bash
uv sync
```

Crea un archivo `.env` en la raíz del proyecto. Sustituye los valores de ejemplo por tus credenciales; no uses estos marcadores como valores reales.

```dotenv
client_id=ID_DE_LA_APLICACION
secret_key=SECRETO_DE_LA_APLICACION
refresh_token=REFRESH_TOKEN
access_token=ACCESS_TOKEN
access_token_expiration_date=2026-10-14T18:00:00+00:00
```

La fecha de expiración debe expresarse en formato ISO 8601, con zona horaria. El comando automatizado presupone que ya existe un refresh token válido: el flujo inicial de autorización y consentimiento OAuth no forma parte de la ejecución principal.

Crea el directorio de datos si aún no existe:

```bash
mkdir -p data
```

En Windows PowerShell, el equivalente es:

```powershell
New-Item -ItemType Directory -Force data
```

Ejecuta el proceso desde la raíz del repositorio:

```bash
uv run python src/main.py
```

La base SQLite se ubica en `data/database.db`. El directorio `.env` se excluye del control de versiones mediante `.gitignore`; no publiques secretos, tokens ni archivos locales de la base de datos.

### Parámetros de configuración

Los parámetros están definidos en `src/config.py`:

| Parámetro | Valor predeterminado | Uso |
|---|---|---|
| `TARGET_MODEL` | `smartphone Samsung Galaxy A16 5g` | Texto de búsqueda del catálogo |
| `DOMAIN_ID` | `MLA-CELLPHONES` | Dominio de celulares en Argentina |
| `PAGINATION_SIZE` | `50` | Tamaño máximo de cada página solicitada |
| `MAX_RESULTS` | `100` | Límite de resultados procesados por ejecución |
| `URL_BASE` | `https://api.mercadolibre.com` | URL base de la API |
| `CATALOG_SEARCH_ENDPOINT` | `/products/search` | Búsqueda de productos del catálogo |
| `PRODUCT_DETAILS` | `/products` | Recurso usado para consultar el detalle de un producto |
| `DATABASE_LOCATION` | `data/database.db` | Ruta local de SQLite |
| `DOT_ENV_FILE` | `.env` | Ruta del archivo de credenciales |

El código envía `condition="new"` junto con los parámetros de búsqueda. Sin embargo, la búsqueda realizada es la de **productos de catálogo**; ese parámetro no debe interpretarse como prueba de que los resultados representen publicaciones de vendedores filtradas por condición.

## 5. Flujo de captura implementado

1. `main()` crea un timestamp UTC `job_run`, inicializa `DatabaseHandler` y garantiza el cierre del engine al finalizar.
2. `extraction()` carga las credenciales, crea `MercadoLibreClientHandler` y verifica el access token.
3. `extract_catalog_data()` prepara la tabla `bronze_product_details` y llama a `paginated_query()` sobre `/products/search` con `site_id=MLA`, `status=active`, `domain_id`, `q`, `condition`, tamaño de página y límite de extracción.
4. Cada página recibida se persiste en `bronze_products`, incluyendo `job_run`, endpoint, texto de búsqueda, resultados JSON, información de paginación, tipo de consulta y dominio.
5. Los IDs de los productos que aparecen en `results` se reúnen en un `set`, con lo que cada ID se procesa una sola vez en esa ejecución.
6. Para cada ID, el cliente consulta `/products/{product_id}`, construye un `CatalogProduct` y lo inserta o actualiza en `bronze_product_details`.

La paginación incluye `limit` y `offset` explícitos. La siguiente posición aumenta según la cantidad de resultados recibidos y el proceso respeta `MAX_RESULTS`.

Las solicitudes HTTP fallidas, respuestas con estructura inesperada o errores de persistencia se propagan y detienen la ejecución. Esto no equivale a una transacción única para todo el ETL: las páginas y los detalles que ya se hayan confirmado en transacciones anteriores permanecen en SQLite. El proceso puede, por tanto, dejar datos parciales si falla después de algunas escrituras; una ejecución interrumpida no debe interpretarse como una carga completa.

## 6. Persistencia

La base usa SQLite y SQLAlchemy. `DatabaseHandler.setup()` crea `bronze_products` y añade las columnas que falten en esa tabla. `DatabaseHandler.create_table(CatalogProduct)` crea `bronze_product_details` según las anotaciones de tipos de la dataclass y añade columnas faltantes a una tabla existente.

Las migraciones implementadas son aditivas: no eliminan ni recrean tablas ni convierten automáticamente datos históricos. Las columnas agregadas a una tabla existente se incorporan sin una restricción `NOT NULL`, para no exigir valores a filas anteriores.

### 6.1 `bronze_products`

Almacena las respuestas brutas de búsqueda: una fila por página procesada. Es una tabla append-only; repetir la búsqueda genera nuevas filas, ya que el flujo no suministra el `id` autogenerado en esas inserciones.

| Campo | Tipo | Nulabilidad |
|---|---|---|
| `id` | INTEGER, clave primaria | No |
| `job_run` | DATETIME | No |
| `endpoint` | VARCHAR | No |
| `keywords` | VARCHAR | Sí |
| `results` | JSON | No |
| `paging` | JSON | No |
| `query_type` | VARCHAR | Sí |
| `domain_id` | VARCHAR | Sí |

DDL equivalente para una base nueva:

```sql
CREATE TABLE IF NOT EXISTS bronze_products (
    id INTEGER PRIMARY KEY,
    job_run DATETIME NOT NULL,
    endpoint VARCHAR NOT NULL,
    keywords VARCHAR,
    results JSON NOT NULL,
    paging JSON NOT NULL,
    query_type VARCHAR,
    domain_id VARCHAR
);
```

En las bases creadas antes de añadir `domain_id`, la inicialización intenta añadir esa columna sin borrar los registros existentes.

### 6.2 `bronze_product_details`

Almacena una fila por producto de catálogo, identificada por `id`. Los detalles se actualizan mediante upsert cuando el mismo ID vuelve a aparecer. En consecuencia, `job_run` refleja la ejecución que escribió el detalle por última vez; esta tabla **no conserva un historial por ejecución** para cada producto.

Las listas y objetos de la respuesta se almacenan como JSON. El DDL siguiente representa el esquema derivado de `CatalogProduct` en el código actual:

```sql
CREATE TABLE IF NOT EXISTS bronze_product_details (
    id VARCHAR PRIMARY KEY NOT NULL,
    job_run DATETIME NOT NULL,
    catalog_product_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    pdp_types JSON NOT NULL,
    domain_id VARCHAR NOT NULL,
    permalink VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    family_name VARCHAR NOT NULL,
    "type" VARCHAR NOT NULL,
    buy_box_winner JSON,
    pickers JSON NOT NULL,
    pictures JSON NOT NULL,
    description_pictures JSON NOT NULL,
    main_features JSON NOT NULL,
    disclaimers JSON NOT NULL,
    attributes JSON NOT NULL,
    short_description JSON NOT NULL,
    parent_id VARCHAR,
    children_ids JSON NOT NULL,
    settings JSON NOT NULL,
    quality_type VARCHAR NOT NULL,
    release_info JSON,
    presale_info JSON,
    enhanced_content JSON,
    tags JSON NOT NULL,
    date_created VARCHAR NOT NULL,
    authorized_stores JSON,
    last_updated VARCHAR NOT NULL,
    grouper_id VARCHAR,
    experiments JSON NOT NULL
);
```

`DatabaseHandler.insert()` usa `id` como clave de conflicto cuando el objeto incluye las columnas de la clave primaria. En `bronze_product_details`, un producto existente se actualiza; en `bronze_products`, las inserciones siguen siendo nuevas filas porque el valor autogenerado `id` no se proporciona.

## 7. Documentación técnica y comportamiento observado de la API

La separación entre catálogo y publicaciones es fundamental para interpretar correctamente el resultado:

- [`/products/search` — Buscador de productos de catálogo](https://developers.mercadolibre.com.ar/es_ar/publica-productos/buscador-de-productos) devuelve productos del catálogo, sus identificadores y metadatos de paginación.
- La misma documentación describe [`/products/{product_id}`](https://developers.mercadolibre.com.ar/es_ar/publica-productos/buscador-de-productos) como recurso para consultar detalles de un producto de catálogo. El campo `buy_box_winner`, cuando existe, identifica una publicación ganadora; no constituye un inventario completo de todas las publicaciones asociadas al producto.
- La documentación de [Ítems y Búsquedas](https://developers.mercadolibre.com.ar/es_ar/guia-para-carrito-de-compras/items-y-busquedas) describe recursos de búsqueda de publicaciones, incluido `/sites/{SITE_ID}/search`.

### Diferencia entre la expectativa inicial y los resultados observados

El enunciado original enumera endpoints de forma general (`/search`, `/items`, `/currencies` y `/currency_conversions`), pero las métricas solicitadas se refieren específicamente a publicaciones y vendedores. Durante el desarrollo fue necesario distinguir dos entidades que no son intercambiables: el producto del catálogo y la publicación comercial de un vendedor.

En las pruebas realizadas, `/products/search` devolvió productos de catálogo, mientras que una solicitud a `/sites/MLA/search` devolvió HTTP 403 con las credenciales y la solicitud utilizadas en ese momento. Ese resultado práctico no coincidió con la expectativa de poder recorrer las publicaciones usando la ruta documentada y consumió tiempo en la investigación de rutas, autenticación y estructura de respuestas. **El HTTP 403 observado no demuestra que la ruta esté universalmente bloqueada ni que su documentación sea incorrecta**; solo registra el comportamiento reproducido en ese contexto.

Para no perder el trabajo ya invertido en la captura de catálogo, se completó la consulta y persistencia de detalles de cada producto encontrado. Esto deja datos reutilizables y un flujo de catálogo reproducible, pero no resuelve la extracción de publicaciones necesaria para las preguntas analíticas.

Otro matiz importante es el filtro `condition="new"`: el código lo envía en la petición de catálogo, pero la documentación del buscador de productos no lo presenta como un filtro de condición de publicación. Por eso no se afirma que la salida de catálogo garantice el requisito de analizar exclusivamente publicaciones nuevas.

## 8. OAuth y protección de credenciales

El `CredentialStoreManager` lee los siguientes campos del archivo `.env` y contiene una rutina para guardar actualizaciones mediante un archivo temporal y reemplazo:

- `client_id`
- `secret_key`
- `access_token`
- `refresh_token`
- `access_token_expiration_date`
- `refresh_token_expiration_date`

El método de renovación persiste el nuevo access token, su expiración y el refresh token renovado. La obtención inicial de tokens por `authorization_code` no está integrada en el flujo ejecutado por `main()`; para ejecutar el proceso se presupone un refresh token previamente obtenido.

El archivo `.env` está incluido en `.gitignore`. No se deben versionar credenciales reales, bases de datos locales ni otros archivos que contengan datos sensibles.

## 9. Pruebas

La versión del repositorio revisada no contiene los archivos `tests/test_api.py`, `tests/test_data_management.py` ni `tests/test_main.py` mencionados en un borrador anterior de esta documentación. Por ello, no se presenta un comando de pruebas automatizadas como validación reproducible de esta entrega.

El criterio de verificación disponible para el flujo es la ejecución del programa con credenciales válidas y la inspección de los registros persistidos en las dos tablas. Una ejecución interrumpida por error puede haber dejado escrituras parciales, por lo que conviene comprobar `job_run`, el número de páginas en `bronze_products` y la cantidad de IDs almacenados en `bronze_product_details` antes de considerar la captura completa.

## 10. Trabajo pendiente para completar el desafío original

1. Resolver y validar el acceso a la búsqueda de publicaciones de vendedores.
2. Extraer los IDs de publicación (no los IDs de catálogo) y persistir las respuestas correspondientes.
3. Normalizar los campos requeridos: `seller_id`, precio, moneda, cantidad vendida, garantía y modalidades de envío.
4. Consultar y registrar la tasa de cambio aplicable para convertir los precios a USD.
5. Definir las tablas analíticas y validar las consultas SQL para las cinco preguntas del desafío.
6. Ejecutar el pipeline con datos de publicaciones completos y verificar que todas las tablas de cada corrida compartan el mismo `job_run`.

## 11. Resumen


La entrega actual implementa la captura de productos de catálogo y sus detalles en SQLite, con paginación, deduplicación en memoria de IDs y upsert de los detalles. La separación entre catálogo y publicación, junto con el HTTP 403 observado en la búsqueda de publicaciones durante el desarrollo, afectó el tiempo disponible para construir la parte analítica. La captura de catálogo se completó para conservar ese avance; los cálculos comerciales del enunciado siguen pendientes porque requieren datos de publicaciones que este flujo aún no extrae.