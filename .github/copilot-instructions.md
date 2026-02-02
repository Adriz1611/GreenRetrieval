# GitHub Copilot Instructions for GreenRetrieval

## Project Overview

GreenRetrieval is an AI-powered retrieval system for plant protection and phytosanitary data, combining the **EPPO Global Database API** with **Groq's LLM services** to enable intelligent querying and analysis of plant pest, disease, and quarantine information.

## Core Architecture

### Data Sources

- **EPPO API** (`api.eppo.int/gd/v2`): Primary source for taxonomic data, pest/host relationships, geographical distribution, regulatory categorization (A1/A2 lists), and reporting service articles
- **EPPO SQLite Export**: Offline database alternative (`eppocodes.sqlite` / `eppocodes_all.sqlite`) with pre-populated taxonomic data, names, and relationships - no API calls or authentication required
- **Groq API** (`api.groq.com`): LLM inference for natural language understanding, query processing, and response generation using models like `llama-3.3-70b-versatile`

### Key Concepts

- **EPPO Codes**: 6-character identifiers for taxa (e.g., `BEMITA` for _Bemisia tabaci_)
- **Taxonomic Hierarchies**: Kingdom → Family → Genus → Species with full classification paths
- **Pest/Host Relationships**: Bidirectional associations with classification labels (Major/Minor)
- **Distribution Status**: Country-level presence with pest status codes and year information
- **Categorization**: Regulatory classifications (A1 list, A2 list, Alert list, Invasive Alien Plants)
- **Regional Organizations**: RPPO codes (e.g., `9A` for EPPO) with member countries

## API Integration Patterns

### EPPO API Authentication

```yaml
Header: X-Api-Key: <token>
Base URL: https://api.eppo.int/gd/v2
Rate Limit: 60 requests per 10-second sliding window
```

### EPPO API Data Retrieval Workflow

1. **Name to Code**: Use `/tools/name2codes?name={taxon_name}` to resolve common names to EPPO codes
2. **Basic Info**: Fetch `/taxons/taxon/{EPPOCODE}/overview` for core metadata
3. **Extended Data**: Query specific endpoints:
   - `/taxons/taxon/{EPPOCODE}/names` - All nomenclature (preferred, scientific, common names by language)
   - `/taxons/taxon/{EPPOCODE}/taxonomy` - Full taxonomic classification
   - `/taxons/taxon/{EPPOCODE}/hosts` or `/pests` - Pest-host relationships
   - `/taxons/taxon/{EPPOCODE}/distribution` - Geographical presence
   - `/taxons/taxon/{EPPOCODE}/categorization` - Regulatory status by country
4. **Cross-References**: Use `/taxons/taxon/{EPPOCODE}/infos` to check available related data counts

### Groq LLM Integration

```python
from groq import Groq

client = Groq()
response = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "You are a plant protection expert..."},
        {"role": "user", "content": "Query about pest data"}
    ],
    model="llama-3.3-70b-versatile",
    temperature=0.5,
    max_completion_tokens=1024
)
```

**Streaming for Real-Time Responses**: Set `stream=True` and iterate over chunks
**Async for Concurrency**: Use `AsyncGroq` client with `await` for non-blocking calls

## EPPO SQLite Database Integration

### Database Versions

**Standard** (`sqlite.zip` → `eppocodes.sqlite`):

- Core taxonomic types: GAI (animals), SIT (animal groups), GAF (microorganisms), SFT (microorganism groups), PFL (plants), SPT (plant groups)

**Extended** (`sqlite_all.zip` → `eppocodes_all.sqlite`):

- Standard types + NTX (non-taxonomic groups), COM (commodities), USE (use categories)
- Includes `t_link_types` table with additional relationship types (9, 10, 11)

### Schema Overview

```sql
-- Core tables
t_codes          -- EPPO codes (codeid, eppocode, dtcode, status, c_date, m_date)
t_names          -- All names (nameid, codeid, fullname, codelang, isocountry, preferred, idauth)
t_links          -- Taxonomic relationships (idlink, codeid, codeid_parent, idlinkcode)
t_authorities    -- Scientific authorities (idauth, authdesc)

-- Reference tables
t_datatypes      -- Data type codes (dtcode, libtype)
t_langs          -- Language codes (codelang, language)
t_countries      -- Country codes (isocountry, country)
t_link_types     -- Link type descriptions (extended version only)
```

### Common Query Patterns

```python
import sqlite3

conn = sqlite3.connect('eppocodes.sqlite')

# Pattern 1: EPPO code → All names
cursor.execute('''
    SELECT n.fullname, n.codelang, n.preferred, l.language
    FROM t_names n
    JOIN t_codes c ON n.codeid = c.codeid
    JOIN t_langs l ON n.codelang = l.codelang
    WHERE c.eppocode = ? AND n.status = 'A'
    ORDER BY n.preferred DESC, n.codelang
''', ('BEMITA',))

# Pattern 2: Name → EPPO code (case-insensitive)
cursor.execute('''
    SELECT DISTINCT c.eppocode, c.dtcode, n.fullname, n.preferred
    FROM t_codes c
    JOIN t_names n ON c.codeid = n.codeid
    WHERE n.fullname LIKE ? AND c.status = 'A'
''', ('%Bemisia tabaci%',))

# Pattern 3: Taxonomic hierarchy (parent → children)
cursor.execute('''
    SELECT c_child.eppocode, c_child.dtcode, n.fullname
    FROM t_links l
    JOIN t_codes c_child ON l.codeid = c_child.codeid
    JOIN t_codes c_parent ON l.codeid_parent = c_parent.codeid
    LEFT JOIN t_names n ON c_child.codeid = n.codeid AND n.preferred = 1
    WHERE c_parent.eppocode = ? AND l.status = 'A'
''', ('1BEMIG',))  # Bemisia genus
```

### Performance Optimizations

- **Pre-configured pragmas**: UTF-8 encoding, 16KB page size, case-insensitive LIKE
- **Indexing strategy**: Add indexes on `t_codes.eppocode`, `t_names.fullname`, `t_links.codeid_parent` for faster queries
- **Status filtering**: Always filter by `status = 'A'` (active) to exclude deprecated records
- **Preferred names**: Use `preferred = 1` for primary nomenclature

### When to Use SQLite vs API

**Use SQLite for**:

- Offline applications or environments without internet access
- High-frequency lookups (no rate limits)
- Bulk data processing and exports
- Name resolution and taxonomic traversal
- Read-only operations on core taxonomy

**Use API for**:

- Real-time distribution data (country presence, pest status)
- Regulatory categorization (A1/A2 lists, Alert lists)
- Reporting Service articles and documents
- Photos, datasheets, and linked resources
- Always-current data (SQLite requires periodic re-download)

## Data Modeling Conventions

### EPPO Code Validation

- 6 characters, alphanumeric uppercase (pattern: `^[A-Z0-9]{6}$`)
- Examples: `BEMITA`, `GOSHI` (Gossypium), `ENCAFO` (Encarsia formosa)

### Country Codes

- ISO 2-letter codes (e.g., `FR`, `US`)
- Special codes for regions (e.g., `9A` for EPPO RPPO)
- Check `/references/countries` for complete list

### Classification References

- **Q-Lists**: `/references/qList` for regulatory list codes (`1`=A1 list, `2`=A2 list)
- **Pest Status**: `/references/distributionStatus` for presence codes
- **Pest/Host Classification**: `/references/pestHostClassification` for relationship types
- **Vector Classification**: `/references/vectorClassification` for transmission modes

## Common Development Patterns

### Pagination Handling

```python
# EPPO API uses offset-based pagination
offset = 0
limit = 100  # Max 1000
all_data = []

while True:
    response = fetch(f"/taxons/list?offset={offset}&limit={limit}")
    all_data.extend(response['data'])
    if len(response['data']) < limit:
        break
    offset += limit
```

### Rate Limit Management

```python
# Monitor headers: x-ratelimit-remaining-requests, x-ratelimit-reset-requests
# Implement exponential backoff on HTTP 429
if response.status_code == 429:
    retry_after = int(response.headers.get('retry-after', 2))
    time.sleep(retry_after)
```

### Error Handling

- **EPPO API**: Handle `400` (bad request), `401` (auth), `404` (not found), `429` (rate limit), `500` (server error)
- **Groq API**: Handle `429` (rate limit), validate token limits (TPM/TPD)

## Reference Data Caching Strategy

Frequently accessed reference endpoints should be cached:

- `/references/countries` - Country/state listings
- `/references/qList` - Regulatory categorization codes
- `/references/distributionStatus` - Pest status codes
- `/references/pestHostClassification` - Relationship classifications
- `/references/rppos` - RPPO organizations

Cache TTL: 24-48 hours (data changes infrequently)

## LLM Context Optimization

### Groq Model Selection

- **`llama-3.3-70b-versatile`**: Default for complex queries (30 RPM, 12K TPM)
- **`llama-3.1-8b-instant`**: Fast responses for simple queries (30 RPM, 6K TPM)
- **Structured Outputs**: Use `response_format={"type": "json_schema", ...}` for guaranteed JSON compliance

### Token Management

- **Prompt Caching**: Groq supports prompt caching (cached tokens don't count toward rate limits)
- **Context Window**: Models support large contexts; condense EPPO data into focused summaries
- **Stop Sequences**: Use `stop=["\n\n", "---"]` to prevent over-generation

## Testing Approach

### Example Test Scenarios

1. **Name Resolution**: "whitefly" → `BEMITA` (Bemisia tabaci)
2. **Host Query**: EPPO code `BEMITA` → List of host plants with classifications
3. **Distribution**: EPPO code + Country → Pest status and year information
4. **Cross-Domain**: "Which countries have A1 list pests from genus Xylella?"

### Validation Points

- EPPO code format correctness
- ISO country code validation
- Null handling for optional fields (`replacedby`, `yr_introd`, `state_id`)
- Relationship bidirectionality (pest ↔ host consistency)

## Documentation Context Files

- **`EPPO_API-Global–Database_context.yaml`**: Complete OpenAPI specification for EPPO endpoints
- **`groq_api_context.md`**: Groq Chat Completions API guide with code examples

When implementing new features:

1. Reference these context files for endpoint signatures and parameters
2. Follow the documented response schemas for data extraction
3. Maintain consistency with naming conventions (e.g., `eppocode`, `prefname`, `country_iso`)

## Development Commands

(Note: No build configuration found in repository; add scripts as project evolves)

```bash
# Expected workflow
pip install groq requests  # Core dependencies
python -m pytest tests/    # Run test suite (when implemented)
python scripts/sync_reference_data.py  # Cache EPPO reference tables
```

## AI Agent Guidance

When querying plant protection data:

1. **Choose the right data source**:
   - Use SQLite for name resolution, taxonomic lookups, and offline queries
   - Use API for distribution, categorization, and always-current data
2. **Always resolve names to EPPO codes first** using `/tools/name2codes` (API) or `t_names` table (SQLite)
3. **Check data availability** with `/taxons/taxon/{EPPOCODE}/infos` before querying specific API endpoints
4. **Combine multiple endpoints/queries** for comprehensive answers (e.g., SQLite taxonomy + API distribution + API categorization)
5. **Format responses with scientific rigor**: Include EPPO codes, preferred names, and data sources
6. **Handle deprecated codes**: Check `replacedby` field (API) or `status = 'A'` filter (SQLite) for active records
