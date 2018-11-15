# coding: utf8

import base64
import datetime
import json
import os
import re
import requests
import shutil
import sys
import tempfile

from bson import ObjectId
from io import BytesIO

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


def format_gift_data(raw_data):
    '''
    raw gift data {'title': ['truc'], 'price': [''], 'location': [''], 'link': [''], 'image': ['']}
    TODO: fix image storing, putting the image in mongodb was pretty shitty anyway (store md5 and url + put image on file storage)
    '''

    gift_data = {
        "title": raw_data["title"][0],
        "price": float(raw_data["price"][0].replace("€", "")),
        "location": raw_data["location"][0]
    }

    # TODO check urls
    gift_data["url"] = raw_data["link"][0]

    # image
    r = requests.get(raw_data["image"][0], stream=True)
    path = "/tmp/gloubi"
    if r.status_code == 200:
        # TODO: it is pretty stupid to save the file and then read it again but storing direct requests binary data in mongo is a mess
        with open(path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f) 

        with open(path, "rb") as f_img:
            encoded_string = base64.b64encode(f_img.read())

        gift_data["image"] = encoded_string

    return gift_data


def get_common_info(sess):
    return {
        "userid": sess.get('logged_as'),
        "username": sess.get('display_name'),
        "people": [{"name": user["name"], "userid": str(user["_id"])} for user in db.users.find({})]
    }



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
            template_data = get_common_info(session)
            return render_template('home.html', **template_data)

    
    @app.route('/addgift')
    def addgift():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        else:
            template_data = get_common_info(session)
            return render_template('addgift.html', **template_data)

    
    @app.route('/addgift', methods=['POST'])
    def insertgift():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        content = request.form.to_dict(flat=False)
        print("raw gift data %s" % str(content), file=sys.stderr)

        try:
            gift_data = format_gift_data(content)
            gift_data["owner"] = ObjectId(session.get('logged_as'))
            db.gifts.insert(gift_data)
        except Exception as e:
            template_data = get_common_info(session)
            template_data["message_type"] = "danger"
            template_data["message_content"] = "Il y a eu une erreur dans le format de vos données, veuillez réessayer. \n %s" % str(e)
            return render_template('message.html', **template_data)

        template_data = get_common_info(session)
        template_data["message_type"] = "success"
        template_data["message_content"] = "Souhait ajouté !"
        return render_template('message.html', **template_data)

    
    @app.route('/giftlist/user/<userid>', methods=["GET"])
    def listgifts(userid):
        if not session.get('logged_in'):
            return redirect("/", code=302)

        user = db.users.find_one({"_id": ObjectId(userid)})
        gifts = db.gifts.find({"owner": ObjectId(userid)})
        template_data = get_common_info(session)
        template_data["gifts"] = list()

        for gift in db.gifts.find({"owner": ObjectId(userid)}):
            template_gift = {k: v for k, v in gift.items() if k in ["title", "price", "location", "url"]}
            template_gift['image'] = gift['image'].decode()
            template_gift['owner'] = str(user['_id'])
            template_gift['owner_name'] = user["name"]

            template_data["gifts"].append(template_gift)

        return render_template('giftlist.html', **template_data)

    
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
            session['logged_as'] = str(user['_id'])
            session['display_name'] = user['name']
        else:
            flash('Wrong password!')

        return redirect("/home", code=302)


    @app.route("/logout")
    def logout():
        session['logged_in'] = False
        session['logged_as'] = None
        session['display_name'] = None
        return redirect("/", code=302)
