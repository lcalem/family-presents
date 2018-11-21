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
from collections import defaultdict
from io import BytesIO

from collections import defaultdict
from pymongo import MongoClient

# from bson import ObjectId
from flask import Flask, request, redirect, render_template, flash, session, abort, g
from werkzeug.datastructures import ImmutableMultiDict
from werkzeug.wrappers import Response

app = Flask(__name__)
app.secret_key = os.urandom(12)


with app.app_context():

    class FormatException(Exception):
        pass

    
    def get_db():
        if not hasattr(g, 'db'):
            db_name = 'mongo%s' % '_prod' if os.environ.get('ENV') == 'prod' else '' 
            client = MongoClient(db_name, 27017)
            db = client.data
            g.db = db
        return g.db


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

        price = int(re.sub("[^0-9]", "", raw_data["price"]))
        if price == 0:
            raise Exception("Les cadeaux gratuits ne sont pas encore gérés ! (mettez un euro symbolique)")

        gift_data = {
            "title": raw_data["title"],
            "price": price,
            "location": raw_data["location"]
        }

        gift_data["remaining_price"] = gift_data["price"]

        # TODO check urls
        gift_data["url"] = raw_data["link"]

        # image
        if not raw_data.get("image"):
            with open("/app/gift.jpg", "rb") as f_img:
                encoded_string = base64.b64encode(f_img.read())
            gift_data["image"] = encoded_string

        else:
            r = requests.get(raw_data["image"], stream=True)
            path = "/tmp/gloubi"
            if r.status_code == 200:
                # TODO: it is pretty stupid to save the file and then read it again but storing direct requests binary data in mongo is a mess
                with open(path, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f) 

                img_size = os.path.getsize(path)
                if img_size > 15000000:
                    raise Exception("Veuillez entrer l'url d'une image plus légère (limite = 15Mb)")

                with open(path, "rb") as f_img:
                    encoded_string = base64.b64encode(f_img.read())

                gift_data["image"] = encoded_string

        return gift_data


    def count_remaining_gifts(userid):
        '''
        gifts: key: user / value: remaining gifts for this user
        counters: various gift counters for shortcuts
        '''
        db = get_db()

        gifts = defaultdict(lambda: 0)
        counters = defaultdict(lambda: 0)
        for gift in db.gifts.find({}):
            # we don't give hints about user's gifts!
            if str(gift["owner"]) == str(userid):
                continue

            if gift["remaining_price"] > 0:
                gifts[str(gift["owner"])] += 1

                if gift["remaining_price"] == gift["price"]:
                    counters["fully_available"] += 1
                else:
                    counters["partially_available"] += 1
            
            else:
                counters["gifted"] += 1
            
            if str(userid) in [str(participation["user"]) for participation in gift.get("participations", [])]:  # meh
                counters["user_participated"] += 1

        return gifts, counters

    def get_common_info(sess):
        info = {
            "userid": sess.get('logged_as'),
            "username": sess.get('display_name')
        }

        db = get_db()

        people = list()
        gifts, counters = count_remaining_gifts(sess.get('logged_as'))
        for user in db.users.find({}):
            people.append({
                "name": user["name"],
                "userid": str(user["_id"]),
                "remaining_gifts": gifts.get(str(user["_id"]), 0)
            })
        info["people"] = people
        info["counters"] = counters

        return info


    def message_template(sess, message_type, message):
        template_data = get_common_info(sess)
        template_data["message_type"] = message_type
        template_data["message_content"] = message
        return render_template('message.html', **template_data)


    def format_gift(db_gift):
        '''
        input: gift object from db
        output: dict formatted for frontend template
        '''
        db = get_db()
        user = db.users.find_one({"_id": db_gift["owner"]})

        template_gift = {k: v for k, v in db_gift.items() if k in ["title", "price", "location", "url", "remaining_price"]}
        template_gift['image'] = db_gift['image'].decode()
        template_gift['owner'] = str(user['_id'])
        template_gift['owner_name'] = user["name"]
        template_gift['_id'] = str(db_gift["_id"])
        return template_gift


    def render_giftlist(session, gifts):
        '''
        renders the giftlist or a generic message if there is no gift to display
        '''

        if len(gifts):
            template_data = get_common_info(session)
            template_data["gifts"] = gifts
            return render_template('giftlist.html', **template_data)

        else:
            return message_template(session, "info", "Il n'y a pas de cadeaux à afficher ici !")


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

        db = get_db()
        content = request.form.to_dict(flat=True)
        print("raw gift data %s" % str(content), file=sys.stderr)

        try:
            gift_data = format_gift_data(content)
            gift_data["owner"] = ObjectId(session.get('logged_as'))
            db.gifts.insert(gift_data)
        except Exception as e:
            return message_template(session, "danger", "Il y a eu une erreur dans le format de vos données, veuillez réessayer. \n %s" % str(e))

        return message_template(session, "success", "Souhait ajouté !")

    
    @app.route('/giftlist/user/<userid>', methods=["GET"])
    def listgifts(userid):
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        gifts = list()
        for gift in db.gifts.find({"owner": ObjectId(userid)}):
            template_gift = format_gift(gift)
            gifts.append(template_gift)

        return render_giftlist(session, gifts)


    @app.route('/giftlist/available', methods=["GET"])
    def list_available():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        gifts = list()
        for gift in db.gifts.find({}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue
            
            if gift["remaining_price"] == gift["price"]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts)

    
    @app.route('/giftlist/completed', methods=["GET"])
    def list_completed():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        gifts = list()
        for gift in db.gifts.find({}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue
            
            if gift["remaining_price"] == 0:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts)

    
    @app.route('/giftlist/started', methods=["GET"])
    def list_started():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        gifts = list()
        for gift in db.gifts.find({}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue
            
            if gift["remaining_price"] > 0 and gift["remaining_price"] < gift["price"]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts)

    
    @app.route('/giftlist/participated/<userid>', methods=["GET"])
    def list_participated(userid):
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        gifts = list()
        for gift in db.gifts.find({}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue
            
            if str(userid) in [str(participation["user"]) for participation in gift.get("participations", [])]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts)


    @app.route('/participate', methods=["POST"])
    def participate():
        '''
        TODO: manage concurrency when we have a big enough family lol
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        data = request.form.to_dict(flat=True)
        print("participation data %s" % str(data), file=sys.stderr)
        if "amount" not in data or "gift_id" not in data:
            return message_template(session, "danger", "participation must contain 'participation' and 'gift_id'!")
    
        gift = db.gifts.find_one({"_id": ObjectId(data["gift_id"])})
        if not gift:
            return message_template(session, "danger", "invalid gift_id")

        try:
            if int(data["amount"]) > gift["remaining_price"]:
                return message_template(session, "danger", "invalid participation! Amount must be less than the remaining price of the gift")
        except ValueError as e:
            return message_template(session, "danger", "participation must be a valid number")

        db.gifts.update_one({"_id": ObjectId(data["gift_id"])}, {
            "$set": {"remaining_price": gift["remaining_price"] - int(data["amount"])},
            "$push": {"participations": {"user": ObjectId(session.get('logged_as')), "amount": data["amount"]}}
        })

        return message_template(session, "success", "Votre participation a bien été enregistrée !")


    @app.route('/login', methods=['POST'])
    def login():
        '''
        TODO: maybe put a real password management here
        '''
        db = get_db()

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
