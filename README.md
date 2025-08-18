# Database Name to Index Mapper

A cross-platform utility for mapping database names to sequential indices. Originally designed for Redis/Valkey database selection, but useful for any scenario where you need consistent string-to-number mapping.

## Features

- **Sequential mapping**: Automatically assigns sequential indices (0, 1, 2, ...) to database names
- **Cross-platform**: Works on Linux, macOS, and Windows with appropriate config paths
- **CLI and Python API**: Use from command line or import as a Python library
- **Utility parameter mapping**: Configure database parameters for different CLI tools
- **Persistent storage**: Mappings are stored in JSON configuration file
- **Prefix filtering**: List mappings by prefix for organized namespacing

## Installation

```bash
pip install db-name-to-idx-mapper
```

## Quick Start

### Command Line Usage

```bash
# Add a new mapping (fails if exists)
db-name-to-idx-mapper add-mapping myapp.cache
# Output: 0
# stderr: Added mapping: myapp.cache -> 0

# Ensure mapping exists (creates if needed, returns existing if present)
db-name-to-idx-mapper ensure-mapping myapp.sessions
# Output: 1

# Map name to index
db-name-to-idx-mapper map myapp.cache
# Output: 0

# List all mappings
db-name-to-idx-mapper list-mappings
# Output:
# myapp.cache:0
# myapp.sessions:1

# List mappings with prefix
db-name-to-idx-mapper list-mappings myapp
# Output:
# myapp.cache:0
# myapp.sessions:1

# Get maximum index (useful for configuring database limits)
db-name-to-idx-mapper get-max-index
# Output: 1

# Configure utility parameter mappings
db-name-to-idx-mapper add-utility-db-param-map redis-cli -n
db-name-to-idx-mapper add-utility-db-param-map redis-benchmark -select

# Get utility parameter
db-name-to-idx-mapper get-utility-db-param redis-cli
# Output: -n

# Execute utility with database mapping
db-name-to-idx-mapper exec redis-cli -n myapp.cache GET somekey
# Executes: redis-cli -n 0 GET somekey

# Execute for multiple databases with prefix
db-name-to-idx-mapper exec redis-cli -n myapp KEYS *
# Executes: redis-cli -n 0 KEYS *
#           redis-cli -n 1 KEYS *
# (for all databases matching "myapp" prefix)
```

### Python API Usage

```python
from db_name_to_idx_mapper import DbNameToIdxMapper

# Initialize mapper
mapper = DbNameToIdxMapper()

# Add mappings
cache_idx = mapper.ensure_mapping("myapp.cache")
session_idx = mapper.ensure_mapping("myapp.sessions")

# Use in your Redis configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://127.0.0.1:6379/{cache_idx}',
    }
}

# List mappings with prefix
app_mappings = mapper.list_mappings("myapp")
for mapping in app_mappings:
    print(f"{mapping['name']} -> {mapping['index']}")

# Get max index for Redis databases configuration
max_idx = mapper.get_max_mapping_index()
redis_databases = max_idx + 1  # Number of databases needed
```

## Configuration

### Config File Location

By default, the configuration file is stored at:
- **Linux**: `/etc/db-name-to-idx-mapper/config.json`
- **macOS**: `~/Library/Application Support/db-name-to-idx-mapper/config.json`
- **Windows**: `%APPDATA%\db-name-to-idx-mapper\config.json`

### Custom Config Path

You can specify a custom config file location using the `--config-path` parameter with system aliases:

```bash
# Use temporary directory
db-name-to-idx-mapper --config-path "{TEMP}/my-config.json" add-mapping test.db

# Use custom path
db-name-to-idx-mapper --config-path "/home/user/my-mappings.json" list-mappings
```

**Available aliases:**
- `{TEMP}`: System temporary directory
- `{CONFIG}`: System configuration directory

### Config File Format

```json
{
  "mappings": {
    "myapp.cache": 0,
    "myapp.sessions": 1,
    "myapp.queue": 2
  },
  "utilities": {
    "redis-cli": "-n",
    "redis-benchmark": "-select",
    "valkey-cli": "-n"
  }
}
```

## Use Cases

### Redis/Valkey Database Management

Instead of remembering database numbers:
```bash
redis-cli -n 0 SET key value  # Which app uses DB 0?
redis-cli -n 1 GET session   # What about DB 1?
```

Use meaningful names:
```bash
# Map names to indices
db-name-to-idx-mapper ensure-mapping myapp.cache    # -> 0
db-name-to-idx-mapper ensure-mapping myapp.sessions # -> 1

# Use with redis-cli (traditional approach with wrapper script)
redis-cli -n $(db-name-to-idx-mapper map myapp.cache) SET key value
redis-cli -n $(db-name-to-idx-mapper map myapp.sessions) GET session:123

# Or use the exec command for cleaner syntax
db-name-to-idx-mapper exec redis-cli -n myapp.cache SET key value
db-name-to-idx-mapper exec redis-cli -n myapp.sessions GET session:123

# Execute commands on all databases with a prefix
db-name-to-idx-mapper exec redis-cli -n myapp FLUSHDB

# Or even create yourself a nice alias:
alias valkey-cli='db-name-to-idx-mapper exec docker exec -i cache valkey-cli'
valkey-cli -n myapp.cache SET key value
```

### Django Multiple Databases

```python
from db_name_to_idx_mapper import DbNameToIdxMapper

mapper = DbNameToIdxMapper()

DATABASES = {
    'users': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': f'app_db_{mapper.ensure_mapping("users")}',
    },
    'analytics': {
        'ENGINE': 'django.db.backends.postgresql', 
        'NAME': f'app_db_{mapper.ensure_mapping("analytics")}',
    }
}
```

### Microservice Port Management

```python
# Assign consistent ports to services
service_port = 8000 + mapper.ensure_mapping("user-service")    # 8000
api_port = 8000 + mapper.ensure_mapping("api-gateway")         # 8001
```

## API Reference

### DbNameToIdxMapper Class

#### Methods

- **`add_mapping(name: str) -> int`**: Add new mapping, raises exception if exists
- **`ensure_mapping(name: str) -> MappingResult`**: Ensure mapping exists, returns `MappingResult(created: bool, index: int)`
- **`map(name: str) -> int`**: Get index for name, raises exception if not found
- **`list_mappings(prefix: str = None) -> List[Dict]`**: List mappings, optionally filtered by prefix
- **`get_max_mapping_index() -> int`**: Get highest mapping index, returns -1 if no mappings
- **`add_utility_db_param_map(utility_name: str, param_name: str)`**: Add utility parameter mapping
- **`get_utility_db_param(utility_name: str) -> str`**: Get utility parameter name

### CLI Commands

All CLI commands output parsable results to stdout and descriptive messages to stderr.

#### Command Reference

- **`exec <utility> [args...]`**: Execute a utility command with automatic database index mapping. If a database name is a prefix (matches multiple mappings), the command runs for all matching databases.

Example:
```bash
# Single database execution
db-name-to-idx-mapper exec redis-cli -n myapp.cache GET key

# Multiple database execution (prefix matching)
db-name-to-idx-mapper exec redis-cli -n myapp KEYS "*"
```

## Requirements

- Python 3.7+
- No external dependencies

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
