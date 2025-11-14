"""
This script provides command line tools for managing a MariaDB database.

It supports the following operations:
- Initialize the database
- Add an entry to the database
- Remove an entry from the database by ID
- List all entries in the database in a readable format

The script uses the mariadb library to connect to the database.
The connection parameters are read from environment variables.

Usage:
- python server-tools.py --init
- python server-tools.py --add "Some data"
- python server-tools.py --remove 1
- python server-tools.py --list
"""

import os
import argparse
import mariadb

def connect_to_db():
    """
    Connect to the MariaDB database using connection parameters from environment variables.
    Returns a connection object.
    """
    conn = mariadb.connect(
        user=os.getenv('DB_USER', 'database_user'),
        password=os.getenv('DB_PASS', 'database_password'),
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '3306')),
        database=os.getenv('DB_NAME', 'licences')
    )
    conn.autocommit = True  # enables autocommit
    return conn

def initialize_db(conn):
    """
    Initialize the database. Creates a table named 'licenses' if it doesn't exist.
    Takes a connection object as argument.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                activation_key TEXT NOT NULL UNIQUE,
                expires_after TIMESTAMP NULL DEFAULT NULL,
                comment TEXT,
                hash TEXT,
                activated_on TIMESTAMP NULL DEFAULT NULL,
                checked_ok_on TIMESTAMP NULL DEFAULT NULL,
                checked_nok_on TIMESTAMP NULL DEFAULT NULL
            )
        """)

def new_activation_key():
    """
    Creates and return a new activation key in hexadecimal string
    """
    activation_key_size = 16    # number of hexadecimal digits (must be even)
    return os.urandom(activation_key_size // 2).hex()

def get_arg_value(args, key_name):
    """
    Retrieve the value of a given key in add arguments
    """
    found_value = None
    for key, value in args:
        if key == key_name:
            found_value = value
            break
    return found_value

def add_entry(conn, arguments):
    """
    Add an entry to the database.
    Takes a connection object and the entry arguments.
    Returns the activation key
    """
    # get entry arguments
    expires_after = get_arg_value(arguments, "expires_after")
    comment = get_arg_value(arguments, "comment")

    # create a new activation key
    activation_key = new_activation_key()

    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO licenses (activation_key, expires_after, comment) 
            VALUES (?, ?, ?)
            """,
            (activation_key, expires_after, comment)
        )
    return activation_key

def remove_entry(conn, entry_id):
    """
    Remove an entry from the database by ID.
    Takes a connection object and the entry ID as arguments.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM licenses WHERE id = ?", (entry_id,))

def list_entries(conn):
    """
    List all entries in the database in a readable format.
    Takes a connection object as argument.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM licenses")
        for (id, activation_key, expires_after, comment, hash, activated_on, checked_ok_on, checked_nok_on) in cur:
            print(f"""
                ID: {id},
                Activation key: {activation_key},
                Expires after: {expires_after},
                Comment: {comment},
                Hash: {hash},
                Activated on: {activated_on},
                Checked OK on: {checked_ok_on},
                Checked NOK on: {checked_nok_on}
                """
            )

def parse_add_arg(arg_string):
    """
    Parse --add argument.
    """
    # check key and value are separated with =
    fields = arg_string.split("=")
    if len(fields) != 2:
        raise argparse.ArgumentTypeError( f"The --add argument '{arg_string}' is not in the format 'key=value'.")
    
    key = fields[0]
    value = fields[1].strip("\"'")  # remove any quotation marks 

    return (key, value)

def main():
    """
    Parse command line arguments and call the appropriate function.
    """
    parser = argparse.ArgumentParser(description='Manage database entries.')
    parser.add_argument('--init',
                        action='store_true',
                        help='Initialize the database')
    parser.add_argument('--add',
                        metavar='FIELD',
                        nargs='+',  # accept multiple arguments separated by space
                        type=parse_add_arg, # use the conversion function
                        help='''Add an entry to the database.
                        Example: --add expires_after=2024-02-01 comment="this is a beautiful entry"''')
    parser.add_argument('--remove',
                        metavar='ID',
                        type=int,
                        help='Remove an entry from the database by ID')
    parser.add_argument('--list',
                        action='store_true',
                        help='List all entries in the database')

    args = parser.parse_args()

    conn = connect_to_db()

    if args.init:
        initialize_db(conn)
    elif args.add:
        arguments = args.add
        activation_key = add_entry(conn, arguments)
        print(f"New licence with activation key '{activation_key}' added")
    elif args.remove:
        remove_entry(conn, args.remove)
    elif args.list:
        list_entries(conn)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
