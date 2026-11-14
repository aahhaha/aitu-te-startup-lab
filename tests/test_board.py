import concurrent.futures,json,sqlite3,threading,urllib.request,urllib.error
import pytest
from app import Board,Problem,make_server

@pytest.fixture
def board(tmp_path):return Board(tmp_path/'test.db')
def question(board,text='How does this work?',**kw):
    return board.submit(dict(room='R1',author='Example student',text=text,request_id='request-0001',**kw))['id']
@pytest.mark.parametrize('size',[1,2,499,500])
def test_valid_boundaries(board,size):assert question(board,'x'*size)>0
@pytest.mark.parametrize('text',['',' ','x'*501,42,None])
def test_invalid_text(board,text):
    with pytest.raises(Problem) as e:question(board,text)
    assert e.value.status==400
def test_public_response_does_not_contain_author(board):
    question(board);public=board.listing();assert 'author' not in public[0]
    assert board.listing(teacher=True)[0]['author']=='Example student'
def test_idempotency_prevents_duplicate_submission(board):
    a=question(board);assert question(board)==a;assert len(board.listing())==1
def test_conflicting_idempotency_key_rejected(board):
    question(board)
    with pytest.raises(Problem) as e:question(board,'A different request')
    assert e.value.status==409
def test_unknown_room_is_not_created(board):
    with pytest.raises(Problem):board.submit(dict(room='R9',author='A',text='q',request_id='request-0002'))
def test_votes_atomic_and_idempotent(board):
    q=question(board)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda _:board.vote(dict(question_id=q,voter_id='same-voter')),range(20)))
    assert board.listing()[0]['votes']==1
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda i:board.vote(dict(question_id=q,voter_id=f'voter-{i:04d}')),range(20)))
    assert board.listing()[0]['votes']==21
def test_hide_answer_restore_transitions(board):
    q=question(board);board.change(dict(question_id=q,answer='A clear answer'),'answer')
    assert board.listing()[0]['status']=='answered'
    board.change(dict(question_id=q,action='hide'),'moderate');assert board.listing()==[]
    with pytest.raises(Problem):board.change(dict(question_id=q,answer='Not visible'),'answer')
    with pytest.raises(Problem):board.vote(dict(question_id=q,voter_id='some-voter'))
    board.change(dict(question_id=q,action='reopen'),'moderate');assert board.listing()[0]['answer']==''
def test_sql_injection_stored_as_data(board):
    question(board,"'; DROP TABLE questions; --");assert len(board.listing())==1
def test_rate_limit_preserves_idempotent_retry(board):
    for i in range(10):board.submit(dict(room='R1',author='A',text='q',request_id=f'request-{i:04d}'))
    assert board.submit(dict(room='R1',author='A',text='q',request_id='request-0000'))['replayed']
    with pytest.raises(Problem) as e:board.submit(dict(room='R1',author='A',text='q',request_id='request-0011'))
    assert e.value.status==429
def test_database_migration_preserves_v1_records(tmp_path):
    f=tmp_path/'old.db'
    with sqlite3.connect(f) as c:
        c.executescript("CREATE TABLE rooms(id TEXT PRIMARY KEY,name TEXT);INSERT INTO rooms VALUES('R1','Old');CREATE TABLE questions(id INTEGER PRIMARY KEY,room TEXT,author TEXT,text TEXT,request_id TEXT,status TEXT,created REAL,UNIQUE(room,author,request_id));INSERT INTO questions VALUES(1,'R1','A','Preserve me','request-old','open',0);PRAGMA user_version=1;")
    b=Board(f);assert b.listing()[0]['text']=='Preserve me';assert b.listing()[0]['answer']==''
    with b.connect() as c:assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert c.execute('PRAGMA user_version').fetchone()[0]==2

@pytest.fixture
def live(tmp_path):
    s=make_server(tmp_path/'http.db','example-teacher-key-for-tests');t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
    yield f'http://127.0.0.1:{s.server_port}'
    s.shutdown();s.server_close();t.join()
def call(url,data=None,key=None):
    r=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+key} if key else {})})
    try:
        with urllib.request.urlopen(r,timeout=5) as res:return res.status,json.load(res)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
def test_http_authorization_and_privacy(live):
    status,q=call(live+'/api/questions',dict(room='R1',author='PrivateName',text='Question',request_id='request-http'))
    assert status==201
    assert call(live+'/api/answer',dict(question_id=q['id'],answer='Answer'))[0]==403
    assert call(live+'/api/moderation')[0]==403
    assert 'PrivateName' not in json.dumps(call(live+'/api/questions')[1])
    assert call(live+'/api/moderation',key='example-teacher-key-for-tests')[1][0]['author']=='PrivateName'
def test_malformed_and_nonobject_json(live):assert call(live+'/api/questions',[1,2])[0]==400
def test_health_and_unknown_path(live):assert call(live+'/health')[0]==200;assert call(live+'/absent')[0]==404
