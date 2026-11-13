# KPMG Sofy Python Test Suite

A Python integration test suite for validating that a Sofy container can execute Python code, load required packages, and perform basic SQL Server read, update, and write operations through the Sofy connection layer.

## Overview

The suite is designed to run inside Sofy's Azure container environment, where the `sofy` object is injected by the platform. The main test flow verifies the Python runtime, confirms `pandas` and `numpy` are usable, reads the active script execution record from Sofy, updates its status, and writes a test DataFrame back into the Sofy database.

## Project Structure

```
.
├── exports.py         # Callable functions exposed to Sofy platform
├── test_suite.py      # Core diagnostic test implementations
├── requirements.txt   # Python dependencies
├── __init__.py        # Package marker
└── README.md          # Documentation
```

## Callable Exports

exports.py exposes two callable entry points:

- `test_database_connection(sofy, record_uuid, db_label='database')`
   Runs the diagnostic suite and returns `SUCCESS` when all steps complete.
- `test_database_connection_debug(sofy, record_uuid, db_label='database')`
   Runs the same suite, but catches exceptions, prints the traceback, and returns a `FAILURE: ...` message for easier debugging in Sofy.

## What The Test Does

The main implementation lives in test_suite.py and performs these checks in order:

1. Prints available Sofy connection factories and the selected database factory.
2. Prints the Python runtime version.
3. Prints the installed `pandas` and `numpy` versions.
4. Verifies `numpy` works by creating an array and calculating summary values.
5. Verifies `pandas` works by creating a small DataFrame and reading aggregate values.
6. Reads `Script` and `Start_time` from `sph_Object_PY_Script_Execution` for the provided `record_uuid`.
7. Updates `script_status` to `container running` for that same record.
8. Creates or truncates `PY_Pandas_Test` and bulk inserts the pandas validation DataFrame.

## Database Behavior

The database test currently targets Sofy's script execution table plus a dedicated pandas test table:

- Read from `sph_Object_PY_Script_Execution` using `UUID = ?`
- Update `sph_Object_PY_Script_Execution.script_status`
- Create or truncate `PY_Pandas_Test`
- Insert the in-memory pandas validation dataset into `PY_Pandas_Test`

The write path is implemented by `write_to_db(...)`, which:

- Infers SQL Server column types from pandas dtypes
- Creates the table if it does not exist
- Truncates the table if it already exists
- Uses `fast_executemany` for batch inserts
- Commits each batch and rolls back on failure
- Skips insertion cleanly when the DataFrame is empty

Example dtype mappings are:

- `int64` → `BIGINT`
- `float64` → `FLOAT`
- `object` → `NVARCHAR(MAX)`
- `bool` → `BIT`
- `datetime64[ns]` → `DATETIME2`

## Usage

Example Sofy invocation:

```python
from exports import test_database_connection

result = test_database_connection(sofy, record_uuid)
```

Debug variant:

```python
from exports import test_database_connection_debug

result = test_database_connection_debug(sofy, record_uuid)
```

## Requirements

requirements.txt currently contains:

- `pandas`
- `numpy`

The Sofy runtime is also expected to provide:

- a working `sofy` object
- a configured database connection for `db_label`
- access to `sph_Object_PY_Script_Execution`
- permission to update `script_status`
- permission to create, truncate, and insert into `PY_Pandas_Test`

## Example Output

```text
Factories: <connection_factories_object>
database factory: <database_connection_factory>
Testing Python runtime and package versions...
Python version: 3.x.x (...)
pandas version: x.y.z
numpy version: x.y.z
✓ Python runtime and package versions detected!

Testing pandas and numpy imports...
NumPy test - Array: [1 2 3 4 5], Mean: 3.0, Sum: 15
Pandas test - DataFrame shape: (3, 3)
Pandas test - Mean age: 30.0
✓ Successfully imported and tested pandas and numpy!

Testing database CRUD operations...
Latest script execution record:
<Script and Start_time output>
✓ Successfully read the active script execution record!

✓ Updated script_status to 'container running' for UUID <record_uuid>
['Name', 'Age', 'Score']
✓ Successfully inserted 3 records to PY_Pandas_Test
   Total time: 0.0 minutes (X rows/sec)
```


## License

KPMG Internal Use
