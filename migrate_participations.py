'''
Migrating b64 images stored in DB to filesystem images
1. read all gifts and convert their image to filesystem image with a path
2. put that path in place of the original data
(optional): put the default image path for gifts that don't have an image
'''
import base64
import hashlib
import os
import sys

from bson import ObjectId
from pymongo import MongoClient


def migrate(dry_run=True):

    # db
    db_name = 'mongo%s' % ('_prod' if os.environ.get('ENV') == 'prod' else '')
    client = MongoClient(db_name, 27017)
    db = client.data

    count_gifts = 0
    count_missing_img = 0
    count_updated = 0
    count_updated_empty = 0

    user_to_name = dict()
    for db_user in db.users.find():
        user_to_name[str(db_user['_id'])] = db_user['name']

    # iterate over gifts
    for db_gift in db.gifts.find():
        count_gifts += 1

        if 'participations' in db_gift:
            new_participations = list()
            for part in db_gift['participations']:
                part['name'] = user_to_name[str(part['user'])]
            new_participations.append(part)

            if not dry_run:
                db.gifts.update_one({"_id": ObjectId(db_gift["_id"])}, {
                    "$set": {"participations": new_participations}
                })
                count_updated += 1
            else:
                print(f'would update {db_gift["_id"]} with participations {new_participations}')

    print(f'gifts {count_gifts} / missing {count_missing_img} / updated {count_updated}')

# python3 migrate_participations.py 1
# python3 migrate_participations.py 0
if __name__ == '__main__':
    dry_run = True
    if len(sys.argv) > 1:
        dry_run = bool(int(sys.argv[1]))

    print(f'Running with dry_run={dry_run}')
    migrate(dry_run)


