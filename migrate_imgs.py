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

    # iterate over gifts
    for db_gift in db.gifts.find():
        count_gifts += 1

        if 'image' not in db_gift:
            count_missing_img += 1

            if not dry_run:
                db.gifts.update_one({"_id": ObjectId(db_gift["_id"])}, {
                    "$set": {"image": 'gift'}
                })
                count_updated += 1

            continue

        b64code = db_gift['image'].decode()
        print(type(b64code))
        imagename = hashlib.md5(b64code.encode('utf-8')).hexdigest()
        imagepath = os.path.join('/app/images', imagename + '.png')
        with open(imagepath, "wb") as fh:
            fh.write(base64.b64decode(b64code))

        if not dry_run:
            db.gifts.update_one({"_id": ObjectId(db_gift["_id"])}, {
                "$set": {"image": imagename}
            })
            count_updated += 1
        else:
            print(f'would update {db_gift["_id"]} with {imagename}')

    print(f'gifts {count_gifts} / missing {count_missing_img} / updated {count_updated}')

# python3 migrate_imgs.py 1
# python3 migrate_imgs.py 0
if __name__ == '__main__':
    dry_run = True
    if len(sys.argv) > 1:
        dry_run = bool(int(sys.argv[1]))

    print(f'Running with dry_run={dry_run}')
    migrate(dry_run)


