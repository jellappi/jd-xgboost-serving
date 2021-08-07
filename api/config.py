db = {
    'user'     : 'root',
    'password' : 'Test1234##',
    'host'     : 'localhost',
    'port'     : 3306,
    'database' : 'db'
}

JWT_SECRET_KEY        = 'SOME_SUPER_SECRET_KEY'
JWT_EXP_DELTA_SECONDS = 7 * 24 * 60 * 60

DB_URL = f"mysql+mysqlconnector://{db['user']}:{db['password']}@{db['host']}:{db['port']}/{db['database']}?charset=utf8"

test_db = {
        'user'     : 'test',
        'password' : 'password',
        'host'     : 'localhost',
        'port'     : 3306,
        'database' : 'test_db'
}

test_config = {
        'DB_URL' : f"mysql+mysqlconnector://{test_db['user']}:{test_db['password']}@{test_db['host']}:{test_db['port']}/{test_db['database']}?charset=utf8"
}
