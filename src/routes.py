import datetime
import json
import os
import re
import sys

from collections import defaultdict
from pymongo import MongoClient

# from bson import ObjectId
from flask import Flask, request, redirect, render_template, flash, session, abort
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.wrappers import Response

app = Flask(__name__)
client = MongoClient('mongo', 27017)
db = client.data


class FormatException(Exception):
    pass


def create_response(error=False, message="", status_code=200, extra_response=None):
    response = {
        "error": error,
        "message": message
    }
    if extra_response:
        response.update(extra_response)

    r = Response(json.dumps(response), mimetype='application/json')
    r.status_code = status_code

    return r


with app.app_context():

    @app.route('/')
    def index():
        if not session.get('logged_in'):
            return render_template('login.html')
        else:
            return redirect("/home", code=302)


    @app.route('/home')
    def home():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        else:
            template_data = {
                "user": session.get('logged_as');
                "user_display_name": session.get('logged_as'),
                "people": [{"name": user["name"], "username": user["username"]} for user in db.users.find({})]
            }
            return render_template('home.html', **template_data)

    
    @app.route('/login', methods=['POST'])
    def login():
        '''
        TODO: maybe put a real password management here
        '''
        user = db.users.find_one({"username": request.form['username']})
        if not user:
            flash('Unknown user %s' % request.form['username'])
        elif request.form['password'] == user['password']:
            session['logged_in'] = True
            session['logged_as'] = user['name']
        else:
            flash('Wrong password!')

        return redirect("/home", code=302)


    @app.route("/logout")
    def logout():
        session['logged_in'] = False
        session['logged_as'] = None
        return redirect("/", code=302)
