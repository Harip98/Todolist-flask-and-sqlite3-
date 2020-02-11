from flask import Flask
from flask_restplus import Api, Resource, fields
from werkzeug.contrib.fixers import ProxyFix
import sqlite3
from sqlite3 import Error
from datetime import datetime
from dateutil import parser

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='1.0', title='TodoMVC API',
    description='A simple TodoMVC API',
)

ns = api.namespace('todos', description='TODO operations')

todo = api.model('Todo', {
    'id': fields.Integer(readonly=True, description='The task unique identifier'),
    'task': fields.String(required=True, description='The task details'),
    'status':fields.String(default = 'Not started',description='Status of the task'),
    'dueby':fields.String(required =True, description='Due date of the task')
})


class TodoDAO(object):
    def __init__(self):
        self.counter = 0
        self.todos = []

    def create_connection(self, db_file = 'db.db'):
        try:
            conn = sqlite3.connect(db_file)
        except Error as e:
            print(e)
        return conn

    def create_table(self):
        conn = self.create_connection()
        table = '''CREATE TABLE IF NOT EXISTS tasks(
                                    id integer PRIMARY KEY,
                                    name text NOT NULL,
                                    dueby text NOT NULL,
                                    status text NOT NULL
                                    );'''
        cur = conn.cursor()
        cur.execute(table)
        conn.commit()

    def create_task(self, task):
        conn = self.create_connection()
        sql = '''INSERT INTO tasks(id, name, dueby, status)
                VALUES (?,?,?,?)'''
        cur = conn.cursor()
        cur.execute(sql, task)
        conn.commit()
        return cur.lastrowid

    def get(self, id):
        for todo in self.todos:
            if todo['id'] == id:
                return todo
        api.abort(404, "Todo {} doesn't exist".format(id))

    def create(self, data):
        todo = data
        todo['id'] = self.counter = self.counter + 1
        todo['dueby']= parser.parse(todo['dueby']).strftime("%Y-%m-%d")
        todo['status'] = todo['status'].capitalize()
        self.todos.append(todo)
        self.create_task((todo['id'], todo['task'], todo['dueby'], todo['status'].capitalize()))
        return todo

    def delete_all_tasks(self):
        conn = self.create_connection()
        sql = ''' DELETE FROM tasks'''
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()

    def update_task(self,task):
        conn = self.create_connection()
        sql = ''' UPDATE tasks
                SET name = ?,
                  dueby = ?,
                  status = ?
                  WHERE id = ?
                '''

        task = (task['task'], task['dueby'], task['status']
                ,str(task['id']))
        cur = conn.cursor()
        cur.execute(sql, task)
        conn.commit()

    def update(self, id, data):
        todo = self.get(id)
        data['status'] = data['status'].capitalize()
        data['dueby'] = parser.parse(data['dueby']).strftime("%Y-%m-%d")
        todo.update(data)
        self.update_task(todo)
        return todo

    def delete_task(self,id):
        conn = self.create_connection()
        sql = ''' DELETE FROM tasks where id = ?'''
        cur = conn.cursor()
        cur.execute(sql, (id,))
        conn.commit()

    def delete(self, id):
        todo = self.get(id)
        self.todos.remove(todo)
        self.delete_task(id)

    def change_status(self, id, stat):
        todo = self.get(id)
        todo.update({'status':stat})
        self.update_task(todo)
        return todo

    def overdue(self):
        conn = self.create_connection()
        #today = datetime.today().strftime("%Y-%m-%d")
        sql = '''SELECT id FROM tasks
                WHERE dueby < strftime('%Y-%m-%d','now') and (status = 'Not started' or status = 'In progress')
                '''
        cur = conn.cursor()
        cur.execute(sql)
        try:
            id_list = cur.fetchall()
        except:
            return {}
        conn.commit()
        todo= []
        for id in id_list:
            todo.append(self.get(id[0]))
        return todo

    def finish(self):
        conn = self.create_connection()
        sql = '''SELECT id FROM tasks
                WHERE status = 'Finished'
                '''
        cur = conn.cursor()
        cur.execute(sql)
        id_list = cur.fetchall()
        print(id_list)
        conn.commit()
        todo= []
        for id in id_list:
            todo.append(self.get(id[0]))
        return todo

    def due(self, dat):
        print(self.todos)
        conn = self.create_connection()
        dat = parser.parse(dat).strftime("%Y-%m-%d")
        sql = '''SELECT id FROM tasks
                WHERE dueby = ? and status != 'Finished'
                '''
        cur = conn.cursor()
        cur.execute(sql,(dat,))
        id_list = cur.fetchall()
        print(id_list)
        conn.commit()
        todo= []
        for id in id_list:
            todo.append(self.get(id[0]))
        print(todo)
        return todo


DAO = TodoDAO()
DAO.create_table()
DAO.delete_all_tasks()
DAO.create({'task': 'Build an API','dueby': '2016.10.16','status':'not started'})
DAO.create({'task': '?????','dueby': '16/10/2016','status':'In progress'})
DAO.create({'task': 'profit!','dueby': '2016/10/10','status':'Finished'})


@ns.route('/')
class TodoList(Resource):
    '''Shows a list of all todos, and lets you POST to add new tasks'''
    @ns.doc('list_todos')
    @ns.marshal_list_with(todo)
    def get(self):
        '''List all tasks'''
        return DAO.todos

    @ns.doc('create_todo')
    @ns.expect(todo)
    @ns.marshal_with(todo, code=201)
    def post(self):
        '''Create a new task'''
        return DAO.create(api.payload), 201


@ns.route('/<int:id>')
@ns.response(404, 'Todo not found')
@ns.param('id', 'The task identifier')
class Todo(Resource):
    '''Show a single todo item and lets you delete them'''
    @ns.doc('get_todo')
    @ns.marshal_with(todo)
    def get(self, id):
        '''Fetch a given resource'''
        return DAO.get(id)

    @ns.doc('delete_todo')
    @ns.response(204, 'Todo deleted')
    def delete(self, id):
        '''Delete a task given its identifier'''
        DAO.delete(id)
        return '', 204

    @ns.expect(todo)
    @ns.marshal_with(todo)
    def put(self, id):
        '''Update a task given its identifier'''
        return DAO.update(id, api.payload)

@ns.route('/<int:id>&<stat>')
@ns.response(404, 'Todo not found')
@ns.param('id','Enter the id')
@ns.param('stat',"Enter the status")
class Todoupdate(Resource):
    '''Update the status'''
    @ns.doc('update_status')
    #@ns.response(201, 'Status updated'
    @ns.marshal_with(todo, code = 201)
    def put(self, id, stat):
        '''Update the status of the id'''
        return DAO.change_status(id, stat),201

@ns.route('/overdue')
class Todooverdue(Resource):
    '''Overdued task'''
    @ns.doc('Overdued task')
    @ns.marshal_with(todo)
    def get(self):
        '''Overdued task'''
        return DAO.overdue()

@ns.route('/finished')
class Todofinish(Resource):
    '''Finished task'''
    @ns.doc('Finished task')
    @ns.marshal_with(todo)
    def get(self):
        '''Finished task'''
        return DAO.finish()

@ns.route('/due<date>')
@ns.param('date','Enter the data')
class Todofinish(Resource):
    ''' due task'''
    @ns.doc('due task')
    @ns.marshal_with(todo)
    def get(self, date):
        '''Due task'''
        return DAO.due(date)


if __name__ == '__main__':
    app.run(debug=True)
