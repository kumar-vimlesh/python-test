import time
import pandas as pd
import numpy as np
import sys
import gc
import io
import traceback
from contextlib import redirect_stdout

# Use SQL new line character for consistent output formatting in Sofy
NEWLINE = chr(10)

# tee stream to capture stdout while still printing to console
class TeeStream:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
        return len(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()

def run(sofy, db_label='database', blob_label=None, debug=False):
    """
    Execute diagnostic tests for Sofy platform integration.
    
    Tests Python runtime, library imports (pandas/numpy), and database CRUD operations.
    
    Args:
        sofy: Sofy platform object with connection factories
        db_label (str): Connection factory label (default: 'database')
        blob_label (str | None): Blob client label to validate through Sofy when provided
        debug (bool): When true, store the full traceback in the Error field
    
    Returns:
        str: 'SUCCESS' if all tests pass
    """

    output_buffer = io.StringIO()

    with sofy.connect(db_label) as cnxn:
        cursor = cnxn.cursor()
        execution_id, execution_df = read_execution_record(cursor)
        update_execution_status(cursor, cnxn, execution_id, 'container running')

        try:
            with redirect_stdout(TeeStream(sys.stdout, output_buffer)):
                # Marker to identify that this output came from vim-python-test-script (test branch)
                print(f"=== Running vim-python-test-script (test branch) ==={NEWLINE}")

                # Print available database connection factories to verify correct setup
                print("Factories:", sofy.connection_factories)
                print(f"{db_label} factory:", sofy.connection_factories.get(db_label))

                # Print Python version and package versions for validation
                print("Testing Python runtime and package versions...")
                print(f"Python version: {sys.version.replace(chr(10), NEWLINE)}")
                print(f"pandas version: {pd.__version__}")
                print(f"numpy version: {np.__version__}")
                print(f"✓ Python runtime and package versions detected!{NEWLINE}")

                # Test pandas and numpy imports
                print("Testing pandas and numpy imports...")

                # Test numpy
                np_array = np.array([1, 2, 3, 4, 5])
                np_mean = np.mean(np_array)
                np_sum = np.sum(np_array)
                print(f"NumPy test - Array: {np_array}, Mean: {np_mean}, Sum: {np_sum}")

                # Test pandas
                test_df = pd.DataFrame({
                    'Name': ['Alice', 'Bob', 'Charlie'],
                    'Age': [25, 30, 35],
                    'Score': [85.5, 92.3, 78.9]
                })
                print(f"Pandas test - DataFrame shape: {test_df.shape}")
                print(f"Pandas test - Mean age: {test_df['Age'].mean()}")
                print(f"✓ Successfully imported and tested pandas and numpy!{NEWLINE}")

                # Database CRUD operations test
                print("Testing database CRUD operations...")

                # Write test DataFrame to the database
                write_to_db(cursor, cnxn, test_df, 'PY_Pandas_Test')

                # Blob storage test through the injected Sofy client
                if blob_label:
                    print("Testing blob storage operations...")
                    test_blob_storage(sofy, blob_label)

            update_execution_output(cursor, cnxn, execution_id, output_buffer.getvalue())
            update_execution_error(cursor, cnxn, execution_id, None)
            update_execution_status(cursor, cnxn, execution_id, 'Completed')
            cnxn.close()
            return 'SUCCESS'
        except Exception as exc:
            error_text = traceback.format_exc() if debug else str(exc)
            update_execution_output(cursor, cnxn, execution_id, output_buffer.getvalue())
            update_execution_error(cursor, cnxn, execution_id, error_text)
            print(error_text)
            raise


def read_execution_record(cursor):
    """Read the latest script execution record and return its ID and details."""

    query = """
    SELECT TOP 1 ID, Script, Start_time
    FROM sph_Object_PY_Script_Execution
    ORDER BY ID DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    columns = [column[0] for column in cursor.description]
    execution_df = pd.DataFrame.from_records(rows, columns=columns)

    if execution_df.empty:
        raise ValueError("No rows found in sph_Object_PY_Script_Execution")

    execution_id = int(execution_df.iloc[0]['ID'])

    print("Latest script execution record:")
    print(execution_df[['ID', 'Script', 'Start_time']].to_string(index=False).replace(chr(10), NEWLINE))
    print(f"✓ Successfully read the active script execution record!{NEWLINE}")

    return execution_id, execution_df


def update_execution_status(cursor, cnxn, execution_id: int, status: str):
    """Update the script execution status for the latest record ID."""

    cursor.execute(
        """
        UPDATE sph_Object_PY_Script_Execution
        SET Status = ?
        WHERE ID = ?
        """,
        status,
        execution_id,
    )
    cnxn.commit()
    print(f"✓ Updated Status to '{status}' for ID {execution_id}{NEWLINE}")


def update_execution_output(cursor, cnxn, execution_id: int, output_text: str):
    """Persist captured stdout to the execution Output field."""

    cursor.execute(
        """
        UPDATE sph_Object_PY_Script_Execution
        SET Output = ?
        WHERE ID = ?
        """,
        output_text,
        execution_id,
    )
    cnxn.commit()


def update_execution_error(cursor, cnxn, execution_id: int, error_text):
    """Persist error text to the execution Error field."""

    cursor.execute(
        """
        UPDATE sph_Object_PY_Script_Execution
        SET Error = ?
        WHERE ID = ?
        """,
        error_text,
        execution_id,
    )
    cnxn.commit()


def test_blob_storage(sofy, blob_label: str):
    """Validate list, write, exists, and read operations through a Sofy blob client."""

    blob_client = sofy.blob_clients[blob_label]
    blob_name = '/input/sofy_blob_test.txt'
    blob_payload = b'Sofy blob test'

    listed_blobs = list(blob_client.list_blobs())
    print(f"Blob list count for '{blob_label}': {len(listed_blobs)}")

    with blob_client.open_stream(blob_name, 'w') as stream:
        stream.write(blob_payload)
    print(f"✓ Wrote blob '{blob_name}' via client '{blob_label}'")

    blob_found = blob_client.exists(blob_name)
    print(f"Blob exists after write: {blob_found}")
    if not blob_found:
        raise ValueError(f"Blob '{blob_name}' was not found after write")

    with blob_client.open_stream(blob_name, 'r') as stream:
        content = stream.read()

    if isinstance(content, str):
        content = content.encode('utf-8')

    if content != blob_payload:
        raise ValueError(f"Blob '{blob_name}' content did not match written payload")

    print(f"✓ Successfully listed, wrote, verified, and read blob '{blob_name}'{NEWLINE}")


def write_to_db(cursor, cnxn, df: pd.DataFrame, table_name: str):
    """
    Write DataFrame to SQL Server table with optimised bulk insertion.
    
    Creates or truncates the table, then inserts data in batches of 10,000 rows.
    
    Args:
        cursor: pyodbc cursor object
        cnxn: pyodbc connection object
        df (pd.DataFrame): DataFrame to write
        table_name (str): Target table name
    """
    
    # Get column names and types for table creation
    columns = df.columns.tolist()
    print(columns)

    dtype_map = {
        'int64': 'BIGINT',
        'float64': 'FLOAT',
        'object': 'NVARCHAR(MAX)',
        'bool': 'BIT',
        'datetime64[ns]': 'DATETIME2'
    }
    
    # Create table if not exists
    create_cols = [f"[{col}] {dtype_map.get(str(df[col].dtypes), 'NVARCHAR(MAX)')}" for col in columns]
    create_statement = f"""
    IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{table_name}')
    CREATE TABLE {table_name} (
        {', '.join(create_cols)}
    )
    ELSE
    TRUNCATE TABLE {table_name}
    """
    cursor.execute(create_statement)
    cnxn.commit()

    if df.empty:
        print(f"✓ Prepared {table_name}, but DataFrame was empty so no rows were inserted")
        return
    
    # Prepare insert statement
    placeholders = ','.join(['?' for _ in columns])
    insert_stmt = f"INSERT INTO {table_name} ({','.join([f'[{col}]' for col in columns])}) VALUES ({placeholders})"
    batch_size=10000

    # Enable fast_executemany for bulk insert performance
    cursor.fast_executemany = True
    
    # Disable autocommit for batch commits
    cnxn.autocommit = False

    start_time = time.time()

    try:
        total_rows = len(df)
        rows_inserted = 0
        # Chunked iteration with itertuples to avoid full-frame copies
        for start in range(0, total_rows, batch_size):

            # Build a list of row tuples only for this chunk
            batch = df.iloc[start:start + batch_size].to_numpy().tolist()

            cursor.executemany(insert_stmt, batch)
            cnxn.commit()
            rows_inserted += len(batch)
            del batch

            # Garbage collect every 20 batches (every ~500k rows with batch_size=10k)
            if (start // batch_size) % 50 == 0:
                gc.collect()


        total_time = time.time() - start_time
        avg_rate = len(df) / total_time if total_time > 0 else 0    
        print(f"✓ Successfully inserted {total_rows:,} records to {table_name}")
        print(f"  Total time: {total_time/60:.1f} minutes ({avg_rate:.0f} rows/sec)")
        
    except Exception as e:
        cnxn.rollback()
        print(f"Error writing to {table_name}: {e}")
        raise

    finally:
        cnxn.autocommit = True
