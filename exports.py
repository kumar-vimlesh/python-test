#Import your callable scripts here
import traceback

import test_suite

# list of callable functions from Sofy, always make sure to include the sofy object as the first argument in your function signature
def test_database_connection(sofy, db_label='database', blob_label=None):
    return test_suite.run(sofy, db_label, blob_label)

# use a try except block to catch any exceptions and return a failure message to Sofy with a traceback for debugging
def test_database_connection_debug(sofy, db_label='database', blob_label=None):
    try:
        return test_suite.run(sofy, db_label, blob_label, debug=True)
    except Exception as e:
        print(f"Error occurred: {e}")
        print(traceback.format_exc())
        return f"FAILURE: {e}"
