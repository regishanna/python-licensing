"""
This module defines a Flask application that provides a license checking service.

The application exposes a single endpoint, /check_license, which accepts GET requests.
The endpoint expects two parameters, 'hash' and 'key', which represent a license 
hash and key respectively.
The application checks the provided license against a database and
returns whether the license is valid.

The database connection parameters are read from environment variables:
- DB_NAME: The name of the database.
- DB_USER: The username to connect to the database.
- DB_PASS: The password to connect to the database.
"""

import os
from datetime import datetime

from flask import Flask, request
from waitress import serve

from server_tools import initialize_db, connect_to_db


app = Flask(__name__)
_conn = None  # pylint: disable=invalid-name


def get_connection():
    """
    Return the database connection.
    """
    global _conn  # pylint: disable=global-statement
    if _conn is None:
        _conn = connect_to_db()
    return _conn

def update_timestamp(key, ts_name):
    """
    Update timestamp of a licence record given the key and
    the name of the timestamp field to be updated
    """
    cur = get_connection().cursor()
    cur.execute(f"UPDATE licenses SET {ts_name}=? WHERE activation_key=?",
                (datetime.now(), key))

def activate_licence(key, hash):
    """
    Activate a licence by storing the received hash
    """
    cur = get_connection().cursor()
    cur.execute(f"UPDATE licenses SET hash=?, activated_on=? WHERE activation_key=?",
                (hash, datetime.now(), key))

def check_license(license_hash, key):
    """
    Check if a license is valid.

    This function checks if a license, represented by a hash and a key, is valid.
    It does this by querying a database.

    Parameters:
    hash (str): The hash of the license.
    key (str): The key of the license.

    Returns:
    bool: True if the license is valid, False otherwise.
    """
    # parameters must by defined
    if (key is None) or (license_hash is None):
        return False

    cur = get_connection().cursor()

    # check key
    cur.execute("SELECT expires_after,hash FROM licenses WHERE activation_key=?",
                (key,))
    result = cur.fetchone()
    if result is None:
        # unknown key
        return False
    else:
        (expires_after, db_hash) = result
        cur.fetchall()  # purge results

    # check expiration
    if (expires_after is not None) and (datetime.now() > expires_after):
        update_timestamp(key, "checked_nok_on")
        return False

    # check if the licence is already activated by hash presence in database
    if db_hash is None:
        # not activated, activate the licence
        activate_licence(key, license_hash)
    else:
        # licence already activated, check hash
        if license_hash != db_hash:
            # bad hash
            update_timestamp(key, "checked_nok_on")
            return False

    # all checks are OK
    update_timestamp(key, "checked_ok_on")
    return True

@app.route('/check_license', methods=['GET'])
def handle_check_license():
    """
    Handle a request to check a license.

    This function handles a GET request to the /check_license endpoint.
    It reads the 'hash' and 'key' parameters from the request, checks if the license is valid,
    and returns a JSON response with the result.

    Returns:
    dict: A dictionary with the keys 'valid' (a boolean indicating if the license is valid)
    and 'message' (a string with a message about the license status).
    """
    license_hash = request.args.get('hash')
    key = request.args.get('key')
    valid = check_license(license_hash, key)
    return {'valid': valid}

if __name__ == '__main__':
    initialize_db(get_connection())

    if os.getenv('ENVIRONMENT', 'production') == 'development':
        print("Running in development mode.")
        app.run(host='0.0.0.0')
    else:
        print("Running in production mode.")
        serve(app, host="localhost", port=os.getenv('LICENSE_PORT', '5000'), threads=4)
