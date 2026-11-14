"""ClearQuestion teaching prototype. Python 3.12, SQLite, loopback HTTP."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import hashlib,hmac,json,os,secrets,sqlite3,time

class Problem(Exception):
    def __init__(self, status, message): self.status,self.message=status,message

class Board:
    def __init__(self, path):
        self.path=str(path)
        with self.connect() as c:
            version=c.execute('PRAGMA user_version').fetchone()[0]
            if version==0:
                c.executescript('''
                CREATE TABLE rooms(id TEXT PRIMARY KEY, name TEXT NOT NULL);
                INSERT INTO rooms VALUES('R1','Demo classroom');
                CREATE TABLE questions(id INTEGER PRIMARY KEY, room TEXT NOT NULL REFERENCES rooms(id),
                  author TEXT NOT NULL, text TEXT NOT NULL, request_id TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','answered','hidden')),
                  created REAL NOT NULL, UNIQUE(room,author,request_id));
                PRAGMA user_version=1;
                ''')
                version=1
            if version==1:
                c.execute("ALTER TABLE questions ADD COLUMN answer TEXT NOT NULL DEFAULT ''")
                c.executescript('''
                CREATE TABLE votes(question_id INTEGER REFERENCES questions(id), voter TEXT NOT NULL,
                  PRIMARY KEY(question_id,voter));
                CREATE TABLE audit(id INTEGER PRIMARY KEY, action TEXT NOT NULL,
                  question_id INTEGER, role TEXT NOT NULL, created REAL NOT NULL);
                CREATE INDEX questions_room ON questions(room,created);
                PRAGMA user_version=2;
                ''')
            elif version!=2: raise RuntimeError('Unsupported schema version')
    @contextmanager
    def connect(self):
        c=sqlite3.connect(self.path,timeout=10)
        c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
        try:
            with c: yield c
        finally:c.close()
    @staticmethod
    def field(data,key,minimum,maximum):
        v=data.get(key)
        if not isinstance(v,str) or not minimum<=len(v.strip())<=maximum:
            raise Problem(400,f'{key} must contain {minimum}-{maximum} characters')
        return v.strip()
    def submit(self,data):
        room=self.field(data,'room',1,20);author=self.field(data,'author',1,80)
        text=self.field(data,'text',1,500);req=self.field(data,'request_id',8,64)
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM rooms WHERE id=?',(room,)).fetchone():raise Problem(404,'Room not found')
            old=c.execute('SELECT id,text FROM questions WHERE room=? AND author=? AND request_id=?',(room,author,req)).fetchone()
            if old:
                if old['text']!=text:raise Problem(409,'Idempotency key used for a different question')
                return {'id':old['id'],'replayed':True}
            recent=c.execute('SELECT COUNT(*) FROM questions WHERE room=? AND author=? AND created>?',(room,author,time.time()-60)).fetchone()[0]
            if recent>=10:raise Problem(429,'Submission limit reached; wait one minute')
            qid=c.execute('INSERT INTO questions(room,author,text,request_id,created) VALUES(?,?,?,?,?)',(room,author,text,req,time.time())).lastrowid
            c.execute("INSERT INTO audit(action,question_id,role,created) VALUES('submit',?,'student',?)",(qid,time.time()))
            return {'id':qid,'replayed':False}
    def listing(self,room='R1',teacher=False):
        with self.connect() as c:
            where='' if teacher else "AND q.status!='hidden'"
            columns=',q.author' if teacher else ''
            rows=c.execute(f'''SELECT q.id,q.room,q.text,q.status,q.answer,q.created,
              (SELECT COUNT(*) FROM votes v WHERE v.question_id=q.id) votes {columns}
              FROM questions q WHERE q.room=? {where} ORDER BY votes DESC,q.id''',(room,)).fetchall()
            return [dict(r) for r in rows]
    def vote(self,data):
        qid=data.get('question_id');voter=self.field(data,'voter_id',8,80)
        if type(qid) is not int:raise Problem(400,'question_id must be an integer')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            q=c.execute('SELECT status FROM questions WHERE id=?',(qid,)).fetchone()
            if not q or q['status']=='hidden':raise Problem(404,'Question not found')
            c.execute('INSERT OR IGNORE INTO votes VALUES(?,?)',(qid,voter))
            return {'votes':c.execute('SELECT COUNT(*) FROM votes WHERE question_id=?',(qid,)).fetchone()[0]}
    def change(self,data,action):
        qid=data.get('question_id')
        if type(qid) is not int:raise Problem(400,'question_id must be an integer')
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT status FROM questions WHERE id=?',(qid,)).fetchone()
            if not row:raise Problem(404,'Question not found')
            if action=='answer':
                if row['status']=='hidden':raise Problem(409,'Restore the hidden question before answering')
                answer=self.field(data,'answer',1,2000)
                c.execute("UPDATE questions SET status='answered',answer=? WHERE id=?",(answer,qid))
            else:
                choice=data.get('action')
                if choice not in ('hide','reopen'):raise Problem(400,'action must be hide or reopen')
                c.execute("UPDATE questions SET status=?,answer=CASE WHEN ?='reopen' THEN '' ELSE answer END WHERE id=?",('hidden' if choice=='hide' else 'open',choice,qid))
            c.execute('INSERT INTO audit(action,question_id,role,created) VALUES(?,?,?,?)',(action,qid,'teacher',time.time()))
            return {'ok':True}

def make_server(path,teacher_key,host='127.0.0.1',port=0):
    if len(teacher_key)<16:raise ValueError('Teacher key must contain at least 16 characters')
    board=Board(path)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def teacher(self):
            supplied=self.headers.get('Authorization','').removeprefix('Bearer ')
            if not hmac.compare_digest(supplied,teacher_key):raise Problem(403,'Teacher authorization required')
        def reply(self,status,data,html=False):
            raw=data.encode() if html else json.dumps(data).encode()
            self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json')
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def dispatch(self,post=False):
            u=urlsplit(self.path)
            if not post:
                if u.path=='/':return self.reply(200,Path(__file__).with_name('index.html').read_text(encoding='utf-8'),True)
                if u.path=='/health':
                    with board.connect() as c:c.execute('SELECT 1').fetchone()
                    return self.reply(200,{'status':'ready'})
                room=parse_qs(u.query).get('room',['R1'])[0]
                if u.path=='/api/questions':return self.reply(200,board.listing(room))
                if u.path=='/api/moderation':self.teacher();return self.reply(200,board.listing(room,True))
                raise Problem(404,'Not found')
            try:n=int(self.headers.get('Content-Length','0'))
            except ValueError:raise Problem(400,'Invalid content length')
            if n<1 or n>16384:raise Problem(413,'Request body too large or empty')
            try:data=json.loads(self.rfile.read(n))
            except (ValueError,UnicodeError):raise Problem(400,'Invalid JSON')
            if not isinstance(data,dict):raise Problem(400,'JSON object required')
            if u.path=='/api/questions':return self.reply(201,board.submit(data))
            if u.path=='/api/votes':return self.reply(200,board.vote(data))
            if u.path in ('/api/answer','/api/moderate'):
                self.teacher();return self.reply(200,board.change(data,'answer' if u.path.endswith('answer') else 'moderate'))
            raise Problem(404,'Not found')
        def safe(self,post=False):
            try:self.dispatch(post)
            except Problem as ex:self.reply(ex.status,{'error':ex.message})
            except sqlite3.Error:self.reply(503,{'error':'Storage temporarily unavailable'})
        def do_GET(self):self.safe()
        def do_POST(self):self.safe(True)
    server=ThreadingHTTPServer((host,port),Handler);server.board=board;return server

if __name__=='__main__':
    key=os.environ.get('TEACHER_KEY') or secrets.token_urlsafe(24)
    server=make_server(os.environ.get('BOARD_DB','board.db'),key,port=int(os.environ.get('PORT','8000')))
    print(f'ClearQuestion: http://127.0.0.1:{server.server_port}; local teacher key: {key}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
