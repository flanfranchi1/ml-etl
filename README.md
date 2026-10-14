# Mercado Libre ETL

Proyecto en Python iniciado para el desafío técnico de automatización ETL con las API de Mercado Libre. El término de búsqueda configurado en el código es `smartphone Samsung Galaxy A16 5g`, y el sitio definido para la consulta es Argentina (`MLA`).

**Estado de la entrega: implementación parcial.** El repositorio contiene código para la configuración, la gestión de credenciales en un archivo, las solicitudes HTTP, la persistencia con SQLite y el inicio de la extracción y transformación. La extracción completa de las publicaciones, el flujo ETL de extremo a extremo y las respuestas analíticas solicitadas en el desafío no se completaron.

## 1. Objetivo del desafío

El enunciado solicita una automatización que consulte las API públicas de Mercado Libre para analizar publicaciones de smartphones Samsung Galaxy nuevos en Argentina y responder las siguientes preguntas:

1. ¿Hay vendedores con múltiples publicaciones? En caso afirmativo, ¿cuántas?
2. ¿Cuál es el promedio de ventas por vendedor?
3. ¿Cuál es el precio promedio en dólares?
4. ¿Cuál es el porcentaje de artículos con garantía?
5. ¿Qué métodos de envío se ofrecen?

El enunciado también exige paginación de 50 registros, la posibilidad de limitar el total consultado, persistencia en una base de datos, un campo `JOB_RUN` con fecha y hora en todas las tablas, documentación del esquema, configuración de parámetros y credenciales fuera del código, instrucciones de instalación y ejecución, DDL y una consulta SQL para cada pregunta de negocio.

## 2. Estructura del repositorio

```text
.
├── README.md
├── pyproject.toml
└── src/
    ├── api.py
    ├── config.py
    ├── data_management.py
    ├── data_modeling.py
    ├── main.py
    └── transformations.py
```

### Archivos implementados

- **`src/api.py`**: define `MercadoLibreClientHandler`, que utiliza `httpx` para realizar solicitudes HTTP autenticadas, contiene rutinas para comprobar y renovar el token e implementa un generador para consultas paginadas.
- **`src/config.py`**: define `CredentialStoreManager` y configura rutas locales, término de búsqueda, tamaño de página y URL de los endpoints.
- **`src/data_management.py`**: define `DatabaseHandler`, crea el engine de SQLAlchemy para SQLite y declara la tabla `bronze_products`.
- **`src/data_modeling.py`**: define modelos de credenciales, de la respuesta bruta de búsqueda y dataclasses relacionadas con publicaciones, atributos, variaciones, direcciones y envíos.
- **`src/transformations.py`**: contiene `get_product_ids`, que obtiene los valores `id` de los elementos encontrados en `results`.
- **`src/main.py`**: contiene las funciones iniciales de extracción y transformación, y el bloque principal de ejecución.
- **`pyproject.toml`**: declara los metadatos, la versión mínima de Python y las dependencias del proyecto.

La existencia de una dataclass para un campo de publicación no significa que ese campo ya se haya extraído, validado o persistido.

## 3. Configuración y dependencias

El archivo `pyproject.toml` declara:

- Python `>=3.12`
- `dotenv>=0.9.9`
- `httpx>=0.28.1`
- `sqlalchemy>=2.1.4`

El código importa `httpx`, `sqlalchemy` y `dotenv`. La instalación de las dependencias y la ejecución completa del proyecto no se han validado de extremo a extremo.

### Parámetros definidos en `src/config.py`

| Parámetro | Valor definido |
|---|---|
| `URL_BASE` | `https://api.mercadolibre.com` |
| `TARGET_MODEL` | `smartphone Samsung Galaxy A16 5g` |
| `PAGINATION_SIZE` | `50` |
| `DATABASE_LOCATION` | `data/database.db`, relativo al directorio de trabajo actual |
| `DOT_ENV_FILE` | `.env`, relativo al directorio de trabajo actual |
| `SEARCH_ENDPOINT` | `https://api.mercadolibre.com/products/search` |
| `CURRENCY_ENDPOINT` | `https://api.mercadolibre.com/currencies` |
| `CURRENCY_EXCHANGE_ENDPOINT` | `https://api.mercadolibre.com/currencies/conversions` |
| `ITENS_ENDPOINT` | `https://api.mercadolibre.com/items` |
| `OAUT_TOKEN_ENDPOINT` | `https://api.mercadolibre.com/oauth/token` |

### Credenciales

El código lee un archivo `.env` en el directorio de trabajo raíz y reconoce los siguientes campos. Los valores son solo marcadores ilustrativos:

```dotenv
client_id=CLIENT_ID_DE_LA_ApLICACIÓN
secret_key=CLIENT_SECRET_VINCULADO_A_LA_APLICACIÓN
access_token=ACCESS_TOKEN_GENERADO_POR_EL_API
refresh_token=TU_REFRESH_TOKEN_GENERADO_POR_LA_API
access_token_expiration_date=FECHA_ISO_8601
```

El código utiliza `dotenv.dotenv_values()` para leer el archivo e incluye una rutina de escritura para actualizar las credenciales. No subas credenciales reales al repositorio. El comportamiento presente en el código utiliza un archivo `.env`; no lee directamente todos los campos desde las variables de entorno del proceso.

## 4. Implementación existente

### Cliente HTTP y OAuth

`MercadoLibreClientHandler` envía el access token en el encabezado `Authorization: Bearer ...`, define un timeout de 30 segundos y llama a `raise_for_status()` en las solicitudes GET. También contiene lógica para renovar el access token cuando falta o está próximo a expirar.

Habia una idea de en caso que sea el primer acceso se podria informar el code obtenido por oauth2 como refresh token para que se pueda generar access y refresh token directamente por la automatización todavia no se llegó a concretizar logica para gestionar el flujo.

### Paginación

El método `paginated_query()` recibe el parámetro `pagination`, pero no lo utiliza para enviar `limit` en la solicitud. El método accede a `kwargs["offset"]`, por lo que las llamadas deben proporcionar ese parámetro. La implementación actual no cumple íntegramente el requisito de paginación efectiva de 50 registros.

### Persistencia

`DatabaseHandler` utiliza SQLAlchemy con SQLite. La tabla `bronze_products` se declara directamente en los metadatos y tiene la siguiente estructura:

| Campo | Tipo SQLAlchemy | Nulabilidad |
|---|---|---|
| `id` | `Integer`, clave primaria | No |
| `job_run` | `DateTime` | No |
| `endpoint` | `String` | No |
| `keywords` | `String` | Sí |
| `results` | `JSON` | No |
| `paging` | `JSON` | No |
| `query_type` | `String` | Sí |

DDL equivalente a la definición existente en el código:

```sql
CREATE TABLE IF NOT EXISTS bronze_products (
    id INTEGER PRIMARY KEY,
    job_run DATETIME NOT NULL,
    endpoint VARCHAR NOT NULL,
    keywords VARCHAR,
    results JSON NOT NULL,
    paging JSON NOT NULL,
    query_type VARCHAR
);
```

La extracción también registra `CatalogProduct` como `bronze_product_details` mediante `DatabaseHandler.create_table()`. Sus columnas se derivan de los tipos de los campos de la dataclass: `id` es la clave primaria, los campos opcionales aceptan `NULL` y los campos de tipo diccionario o lista se almacenan como JSON. Esta tabla se crea en la base de datos al llamar a `create_table()`.

`DatabaseHandler.insert()` realiza un upsert cuando el objeto contiene las columnas de clave primaria de su tabla: si ya existe una fila con esa clave, actualiza sus demás campos; de lo contrario, inserta una fila nueva. Esto permite volver a cargar un `CatalogProduct` con el mismo `id` sin provocar una violación de unicidad. Los registros de `bronze_products` no incluyen su `id` autogenerado, por lo que se insertan como filas nuevas.

El método `DatabaseHandler.setup()` crea las tablas ya registradas en los metadatos. Como la ruta configurada incluye el directorio `data/`, ese directorio debe existir para que el archivo de la base de datos pueda crearse allí.

El campo está escrito como `job_run` en el código. Aunque `src/main.py` define una marca de tiempo para la ejecución, el flujo actual no se ha validado de extremo a extremo para confirmar que todas las escrituras utilizan la misma marca de tiempo.

## 5. Intentos de acceso a la API

Durante las pruebas registradas en el desarrollo:

- La llamada a `/products/search` devolvió datos de productos de catálogo.
- La búsqueda de publicaciones en `/sites/MLA/search` devolvió HTTP 403 en el entorno utilizado.
- Una respuesta consultada mediante `/products/{product_id}` contenía datos de catálogo, incluidos `buy_box_winner: null`, `parent_id` y `children_ids`.

Estos resultados describen las respuestas observadas en las pruebas realizadas. No demuestran que todos los endpoints de búsqueda de publicaciones siempre devuelvan HTTP 403, ni que no existan publicaciones asociadas al producto consultado.

Las preguntas del desafío se refieren a publicaciones y vendedores. El flujo actual no completa la obtención de los datos de publicación necesarios para calcular el número de publicaciones por vendedor, las ventas, los precios, la garantía y las modalidades de envío.

Documentación general indicada en el enunciado: [Mercado Libre Developers](https://developers.mercadolibre.com/).

## 6. Limitaciones concretas del flujo principal

El bloque principal de `src/main.py` crea el `DatabaseHandler`, llama a `setup()`, deja comentada la llamada a `extraction()`, llama a `transformation()` y después a `extraction_itens(ids)`.

Las funciones todavía no forman un flujo completo:

- `extraction()` añade `job_run` y `endpoint` al objeto de respuesta antes de instanciar `ProductsQueryRawOutput`. Esta dataclass también requiere `keywords` y `query_type`, que la función no añade a partir de la respuesta en ese fragmento.
- `transformation()` lee los registros de `bronze_products` y utiliza `get_product_ids()` para extraer IDs de `results`. En el código, esta función devuelve los valores `id` presentes en la respuesta de búsqueda; esto no demuestra que sean IDs de publicaciones de vendedores.
- `extraction_itens()` no proporciona el parámetro `offset` que exige el generador de paginación y no utiliza los IDs recibidos para construir una llamada específica a un ítem o una llamada por lotes.
- Por estos motivos, el punto de entrada actual no ejecuta una extracción inicial ni una carga analítica completa.

## 7. Elementos del desafío que no se entregaron

En el estado actual del repositorio, no están implementados o validados:

- Extracción completa de las publicaciones de vendedores.
- Paginación efectiva con `limit=50` y control validado del total extraído.
- Carga de respuestas de publicaciones y transformación de los campos necesarios para el análisis.
- Tablas analíticas normalizadas para vendedor, precio, moneda, cantidad vendida, garantía y envío.
- Carga y uso validado de tasas de conversión a USD.
- Consultas SQL validadas para las cinco preguntas de negocio.
- Resultados numéricos fiables para responder las preguntas.
- Ejecución ETL de extremo a extremo demostrada y validada.

Estas carencias se registran para delimitar lo que realmente se entregó. Este README no presenta tablas hipotéticas, consultas que dependan de tablas inexistentes ni resultados no calculados como si fueran parte de la implementación.

## 8. Resumen

El proyecto contiene una base inicial para el acceso HTTP autenticado a la API de Mercado Libre, la gestión de credenciales en un archivo, la configuración de parámetros, la persistencia raw con SQLite/SQLAlchemy y modelos de datos iniciales. La integración y el flujo de transformación necesarios para responder las preguntas del desafío siguen incompletos.
