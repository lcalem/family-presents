# coding: utf8

import base64
import datetime
import hashlib
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
            db_name = 'mongo%s' % ('_prod' if os.environ.get('ENV') == 'prod' else '')
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

    def format_update_data(raw_data):
        update_data = {}

        if raw_data.get('price'):
            m = re.match(r"^[0-9]*([,|.]{0,1}[0-9]+)", raw_data["price"])
            price = float(m.group(0).replace(',', '.'))

            if price == 0:
                raise Exception("Les cadeaux gratuits ne sont toujours pas gérés ! (mettez un euro symbolique)")

            update_data['price'] = price
            update_data['remaining_price'] = price

        if raw_data['title']:
            update_data['title'] = raw_data['title']

        if raw_data['location']:
            update_data['location'] = raw_data['location']

        if raw_data['link']:
            update_data["url"] = raw_data["link"]

        if raw_data['image']:
            update_data["image"] = format_image_data(raw_data['image'])

        return update_data


    def format_gift_data(raw_data):
        '''
        formatting user input
        raw gift data {'title': ['truc'], 'price': [''], 'location': [''], 'link': [''], 'image': ['']}
        TODO: fix image storing, putting the image in mongodb was pretty shitty anyway (store md5 and url + put image on file storage)
        '''

        m = re.match(r"^[0-9]*([,|.]{0,1}[0-9]+)", raw_data["price"])
        price = float(m.group(0).replace(',', '.'))

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
        gift_data["image"] = format_image_data(raw_data.get('image'))

        return gift_data


    def format_image_data(image_field):
        if not image_field:
            return 'gift'

        elif image_field.startswith('data:image/') and ';base64,' in image_field:
            # data:image/jpeg;base64 style images in URL
            b64code = image_field.split(';base64,')[1]
            imagename = hashlib.md5(b64code.encode('utf-8')).hexdigest()
            imagepath = os.path.join('/app/images', imagename + '.png')
            with open(imagepath, "wb") as fh:
                fh.write(base64.b64decode(b64code))
            return imagename

        else:
            imagename = hashlib.md5(image_field.encode('utf-8')).hexdigest()
            imagepath = os.path.join('/app/images', imagename + '.png')

            r = requests.get(image_field, stream=True)
            if r.status_code == 200:
                with open(imagepath, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)

                return imagename
            else:
                return 'gift'


    def count_remaining_gifts(userid):
        '''
        gifts: key: user / value: remaining gifts for this user
        counters: various gift counters for shortcuts
        '''
        db = get_db()

        user = db.users.find_one({'_id': ObjectId(userid)})
        user_families = user['families']

        gifts = defaultdict(lambda: 0)
        counters = defaultdict(lambda: 0)
        for gift in db.gifts.find({"owner_families": {"$in": user_families}}):
            # we don't give hints about user's gifts!
            if str(gift["owner"]) == str(userid):
                continue

            if 'price' not in gift:
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
        '''
        Gets general display info such as:
        - every people you can see (filtered by family visibility)
        - their gift counters
        '''
        info = {
            "userid": sess.get('logged_as'),
            "username": sess.get('display_name')
        }

        db = get_db()

        user = db.users.find_one({'_id': ObjectId(sess.get('logged_as'))})
        user_families = user['families']

        people = list()
        gifts, counters = count_remaining_gifts(sess.get('logged_as'))
        for user in db.users.find({"families": {"$in": user_families}}):
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


    def delete_message_template(sess, gift_id):
        template_data = get_common_info(sess)
        template_data["giftid"] = gift_id
        return render_template('message_delete.html', **template_data)


    def format_gift(db_gift):
        '''
        input: gift object from db
        output: dict formatted for frontend template
        '''
        db = get_db()
        user = db.users.find_one({"_id": db_gift["owner"]})

        template_gift = {k: v for k, v in db_gift.items() if k in ["title", "price", "location", "url", "remaining_price", "participations"]}

        template_gift['owner'] = str(user['_id'])
        template_gift['owner_name'] = user["name"]
        template_gift['_id'] = str(db_gift["_id"])

        # image
        imagepath = os.path.join('/app/images', db_gift['image']) + '.png'
        with open(imagepath, "rb") as f_img:
            encoded_string = base64.b64encode(f_img.read())
            template_gift['image'] = encoded_string.decode()  # TODO check if we can use the .read() directly?

        if 'price' in db_gift:
            price = db_gift['price']
            # if price is int then drop the decimal part
            if int(price) == price:
                template_gift['price'] = '~ ' + str(int(price))

        return template_gift


    def render_giftlist(session, gifts, title):
        '''
        renders the giftlist or a generic message if there is no gift to display
        '''

        if len(gifts):
            template_data = get_common_info(session)
            template_data["gifts"] = gifts
            template_data["title"] = title
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
        # print("raw gift data %s" % str(content), file=sys.stderr)

        # we copy family for each gift for easier counting / filtering
        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        try:
            gift_data = format_gift_data(content)
            gift_data["owner"] = ObjectId(session.get('logged_as'))
            gift_data["owner_families"] = user_families
            db.gifts.insert(gift_data)
        except Exception as e:
            return message_template(session, "danger", "Il y a eu une erreur dans le format de vos données, veuillez réessayer. \n %s" % str(e))

        return message_template(session, "success", "Souhait ajouté !")


    @app.route('/addsurprise')
    def addsurprise():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        # we copy family for each gift for easier counting / filtering
        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        try:
            gift_data = {
                'title': 'Faites-moi une surprise!',
                'location': 'Votre imagination',
                'image': 'surprise',
                'owner': ObjectId(session.get('logged_as')),
                'owner_families': user_families
            }

            db.gifts.insert(gift_data)
        except Exception as e:
            return message_template(session, "danger", "Il y a eu une erreur dans le format de vos données, veuillez réessayer. \n %s" % str(e))

        return message_template(session, "success", "Surprise ajoutée !")


    @app.route('/giftlist/user/<userid>', methods=["GET"])
    def listgifts(userid):
        '''
        Lists gifts for a perticular user
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()
        user = db.users.find_one({"_id": ObjectId(userid)})

        gifts = list()
        for gift in db.gifts.find({"owner": ObjectId(userid)}):
            template_gift = format_gift(gift)
            gifts.append(template_gift)

        return render_giftlist(session, gifts, "Les souhaits de %s" % user["name"])


    @app.route('/giftlist/available', methods=["GET"])
    def list_available():
        '''
        Lists all available gifts
        (filtered by family visibility)
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        gifts = list()
        for gift in db.gifts.find({"owner_families": {"$in": user_families}}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue

            if gift["remaining_price"] == gift["price"]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts, "Les souhaits disponibles")


    @app.route('/giftlist/completed', methods=["GET"])
    def list_completed():
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        gifts = list()
        for gift in db.gifts.find({"owner_families": {"$in": user_families}}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue

            if gift["remaining_price"] == 0:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts, "Les souhaits déjà offerts")


    @app.route('/giftlist/started', methods=["GET"])
    def list_started():
        '''
        Route for listing gifts that are partly gifted
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        gifts = list()
        for gift in db.gifts.find({"owner_families": {"$in": user_families}}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue

            if gift["remaining_price"] > 0 and gift["remaining_price"] < gift["price"]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts, "Les souhaits où il manque une contribution")


    @app.route('/giftlist/participated/<userid>', methods=["GET"])
    def list_participated(userid):
        '''
        Route for gifts where the user has contributed
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        user = db.users.find_one({'_id': ObjectId(session.get('logged_as'))})
        user_families = user['families']

        gifts = list()
        for gift in db.gifts.find({"owner_families": {"$in": user_families}}):
            if str(gift["owner"]) == session.get('logged_as'):
                continue

            if str(userid) in [str(participation["user"]) for participation in gift.get("participations", [])]:
                template_gift = format_gift(gift)
                gifts.append(template_gift)

        return render_giftlist(session, gifts, "Les souhaits auxquels j'ai participé")


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


    @app.route('/deletegift/<giftid>', methods=["GET"])
    def deletegift(giftid):
        '''
        Delete a particular gift: cannot delete if someone already made a contribution
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        gift = db.gifts.find_one({"_id": ObjectId(giftid)})
        if not gift:
            return message_template(session, "danger", "Le cadeau n'existe pas !")

        elif str(gift['owner']) != session['logged_as']:
            return message_template(session, "danger", "Vous ne pouvez pas supprimer un cadeau qui n'est pas à vous !")

        elif 'price' in gift and gift["remaining_price"] != gift["price"]:
            return delete_message_template(session, giftid)
        else:
            db.gifts.delete_one({"_id": ObjectId(giftid)})
            return message_template(session, "success", "Cadeau supprimé")


    @app.route('/forcedelete/<giftid>', methods=["GET"])
    def forcedeletegift(giftid):
        '''
        Force delete a particular gift: for when we got the gift
        '''
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        gift = db.gifts.find_one({"_id": ObjectId(giftid)})
        if not gift:
            return message_template(session, "danger", "Le cadeau n'existe pas !")

        elif str(gift['owner']) != session['logged_as']:
            return message_template(session, "danger", "Vous ne pouvez pas supprimer un cadeau qui n'est pas à vous !")

        else:
            db.gifts.delete_one({"_id": ObjectId(giftid)})
            return message_template(session, "success", "Cadeau supprimé")


    @app.route('/updategift/<giftid>', methods=["GET"])
    def updategiftform(giftid):
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        gift = db.gifts.find_one({"_id": ObjectId(giftid)})
        if not gift:
            return message_template(session, "danger", "Le cadeau n'existe pas !")

        elif str(gift['owner']) != session['logged_as']:
            return message_template(session, "danger", "Vous ne pouvez pas supprimer un cadeau qui n'est pas à vous !")

        else:
            template_data = get_common_info(session)
            template_data['gift'] = gift
            template_data['disabled'] = 'disabled' if gift['price'] != gift['remaining_price'] else ''

            return render_template('updategift.html', **template_data)


    @app.route('/updategift/<giftid>', methods=["POST"])
    def updategift(giftid):
        if not session.get('logged_in'):
            return redirect("/", code=302)

        db = get_db()

        gift = db.gifts.find_one({"_id": ObjectId(giftid)})
        if not gift:
            return message_template(session, "danger", "Le cadeau n'existe pas !")

        elif str(gift['owner']) != session['logged_as']:
            return message_template(session, "danger", "Vous ne pouvez pas supprimer un cadeau qui n'est pas à vous !")

        else:
            content = request.form.to_dict(flat=True)
            print("raw gift data %s" % str(content), file=sys.stderr)

            try:
                update_data = format_update_data(content)

                db.gifts.update_one({"_id": ObjectId(giftid)}, {"$set": update_data})
            except Exception as e:
                return message_template(session, "danger", f"Erreur lors de la mise à jour {str(e)}")

            return message_template(session, "success", "Cadeau mis à jour")


    @app.route('/login', methods=['POST'])
    def login():
        '''
        check md5 hash of password
        '''
        db = get_db()

        user = db.users.find_one({"username": request.form['username']})
        if not user:
            flash('Unknown user %s' % request.form['username'])
        elif hashlib.md5(request.form['password'].encode('utf-8')).hexdigest() == user['password']:
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
