import jwt
import bcrypt
import re
import nltk
import pickle

from flask       import Flask, request, jsonify, current_app, Response, g
from flask.json  import JSONEncoder
from sqlalchemy  import create_engine, text
from datetime    import datetime, timedelta
from functools   import wraps
from konlpy.tag  import Kkma

import pandas  as pd
import xgboost as xgb

# nlp instance
kkma = Kkma()
wlem = nltk.WordNetLemmatizer()

# load data
prefix = '/home/ubuntu'

columns = list(pd.read_csv(f'{prefix}/data/preprocessed_data.csv', nrows=0).columns)
columns.remove('category')

encoding = pd.read_csv(f'{prefix}/data/category_encoding.csv', sep='\t', index_col=0)

model = pickle.load(open(f'{prefix}/model/xgb-model', 'rb'))


# Custom JSON Encoder which transforms set into list
# (HTTP can't send set)
class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)

        return JSONEncoder.default(self, obj)

def get_user(user_id):
    user = current_app.database.execute(text("""
        SELECT 
            id,
            name,
            email
        FROM users
        WHERE id = :user_id
    """), {
        'user_id' : user_id 
    }).fetchone()

    return {
        'id'      : user['id'],
        'name'    : user['name'],
        'email'   : user['email'],
    } if user else None

def insert_user(user):
    return current_app.database.execute(text("""
        INSERT INTO users (
            name,
            email,
            hashed_password
        ) VALUES (
            :name,
            :email,
            :password
        )
    """), user).lastrowid

def get_user_id_and_password(email):
    row = current_app.database.execute(text("""    
        SELECT
            id,
            hashed_password
        FROM users
        WHERE email = :email
    """), {'email' : email}).fetchone()

    return {
        'id'              : row['id'],
        'hashed_password' : row['hashed_password']
    } if row else None

def extract_kor(string):
    
    #kkma = Kkma()
    
    text_data = [] 
    
    ex_pos = kkma.pos(string)
    
    for (text, tclass) in ex_pos : # ('형태소', 'NNG') 
        if tclass == 'NNG' or tclass == 'NNP' or tclass == 'NP' : 
            text_data.append(text)  
            
    return text_data


def extract_eng(string):
    
    #wlem = nltk.WordNetLemmatizer()
    
    cleaned_content = re.sub(r'[^\.\?\!\w\d\s]', '', string)
    
    word_tokens = nltk.word_tokenize(cleaned_content)
    tokens_pos = nltk.pos_tag(word_tokens)
    
    NN_words = []
    for word, pos in tokens_pos:
        if 'NN' in pos:
            NN_words.append(word.lower())
            
    lemmatized_words = []
    for word in NN_words:
        new_word = wlem.lemmatize(word)
        lemmatized_words.append(new_word)
        
    return lemmatized_words

#########################################################
#       Decorators
#########################################################
def login_required(f):      
    @wraps(f)                   
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization') 
        if access_token is not None:  
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], 'HS256') 
            except jwt.InvalidTokenError:
                 payload = None     

            if payload is None: return Response(status=401)  

            user_id   = payload['user_id']  
            g.user_id = user_id
            g.user    = get_user(user_id) if user_id else None
        else:
            return Response(status = 401)  

        return f(*args, **kwargs)
    return decorated_function

def create_app(test_config = None):
    app = Flask(__name__)

    app.json_encoder = CustomJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database     = create_engine(app.config['DB_URL'], encoding = 'utf-8', max_overflow = 0)
    app.database = database

    # @app.route("/ping", methods=['GET'])
    # def ping():
    #     return "pong"

    @app.route("/sign-up", methods=['POST'])
    def sign_up():
        new_user    = request.json
        new_user['password'] = bcrypt.hashpw(
            new_user['password'].encode('UTF-8'),
            bcrypt.gensalt()
        )

        new_user_id = insert_user(new_user)
        new_user    = get_user(new_user_id)

        return jsonify(new_user)
        
    @app.route('/login', methods=['POST'])
    def login():
        credential      = request.json
        email           = credential['email']
        password        = credential['password']
        user_credential = get_user_id_and_password(email)

        if user_credential and bcrypt.checkpw(password.encode('UTF-8'), user_credential['hashed_password'].encode('UTF-8')): 
            user_id = user_credential['id'] 
            payload = {     
                'user_id' : user_id,
                'exp'     : datetime.utcnow() + timedelta(seconds = 60 * 60 * 24)
            }
            token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], 'HS256') 

            return jsonify({        
                'access_token' : token.decode('UTF-8')
            })
        else:
            return '', 401
    
    @app.route('/infer', methods=['POST'])
    @login_required
    def infer():
        jd       = request.json
        jd['id'] = g.user_id
        
        # extract
        if (jd['position'] == None) & (jd['main_tasks'] == None):
            print("No input data. At least one of position and main_tasks is needed.")

        elif jd['position'] != None:
            ex = extract_kor(jd['position'])

            if len(ex) == 0:
                ex = extract_eng(jd['position'])

        else:
            ex = extract_kor(jd['main_tasks'])

            if len(ex) == 0:
                ex = extract_eng(jd['main_tasks'])
                
        
        # request preprocessing
        df = pd.DataFrame(columns=columns)
        df.loc[len(df)] = 0

        for col in columns:
            df[col] = df[col].astype('int')

        for w in ex:
            if w in df.columns:
                df.loc[0, w] = 1
                
        df = df[sorted(df.columns)]

        dtest = xgb.DMatrix(data=df)
        
        
        # inference
        predicted_code = int(model.predict(dtest)[0])
        infer_result = encoding.loc[predicted_code, 'category']

        
        return jsonify({
            'category' : infer_result
        })
    

    return app

