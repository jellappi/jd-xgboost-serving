import config
import pytest
import bcrypt

from app import create_app
from sqlalchemy import create_engine, text

database = create_engine(config.test_config['DB_URL'], encoding='utf-8', max_overflow=0)

@pytest.fixture
def api():
    app = create_app(config.test_config)
    app.config['TEST'] = True
    api = app.test_client()

    return api


def test_ping(api):
    resp = api.get('/ping')
    assert b'pong' in resp.data

# codes before each tests
def setup_function():
    ## Create a test user
    hashed_password = bcrypt.hashpw(
        b"test password",
        bcrypt.gensalt()
    )
    new_users = [
        {
            'id'              : 1,
            'name'            : 'songha',
            'email'           : 'amaranth7219@gmail.com',
            'hashed_password' : hashed_password
        },
        {
            'id'              : 2,
            'name'            : 'chulsu',
            'email'           : 'chulsu@chulsu.com',
            'hashed_password' : hashed_password
        }
    ]
    database.execute(text("""
        INSERT INTO users (
            id,
            name,
            email,
            hashed_password
        ) VALUES (
            :id,
            :name,
            :email,
            :hashed_password
        )
    """), new_users)

# codes after each tests
def teardown_function():
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE users"))
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def test_infer(api):
    ## login
    resp = api.post(
            '/login',
            data = json.dumps({
                'name': 'songha',
                'email': 'amaranth7219@gmail.com',
                'password': 'test password'
                }),
            content_type = 'application/json'
    )
    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']

    ## infer
    resp = api.post(
            'infer',
            data = json.dumps({
                'main_tasks': '• 데이터 모델링을 통한 전사과제 해결 • 추천/개인화 모델 고도화 • 쇼핑몰 랭킹 고도화 • 지그재그 상품인기도 고도화 • 광고수익 예측을 통한 효율적인 광고소재 관리 제공 • 상품 메타데이터 자동 생성 및 관리 • 사용자 리뷰데이터 분석을 위한 텍스트 모델링',
                'position': '지그재그 데이터 사이언티스트',
                'preferred_points': '• 프로덕션 레벨의 ML모델 개발 프로세스에 대한 이해가 높고 경험이 있으신분 • 데이터 분석가/엔지니어 및 타 팀과의 커뮤니케이션이 원활하신 분 • 데이터 엔지니어링 및 분산처리, 서버개발 경험 • 사용하는 기술의 원리를 깊게 파악하고, 실무에 적용해보신 분',
                'requirements': '• 주요업무의 과제 중 한가지는 자신 있으신분 • 데이터 모델링을 통해 비즈니스 문제를 해결해 보신 분 • 클라우드 환경에서의 데이터 모델링 경험이 있으신 분 (AWS 경험 선호) • Python 프로그래밍 언어에 능숙하신 분 • Tensorflow, Keras, PyTorch 같은 딥러닝 프레임워크 사용에 익숙하신분'
            }),
            content_type = 'application/json',
            headers = {'Authorization': access_token}
    )
    assert resp.status_code == 200


