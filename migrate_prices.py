'''
Prices -> floored prices
'''
import os
import sys
import math

from bson import ObjectId
from pymongo import MongoClient


def migrate(dry_run=True):

    # db
    db_name = 'mongo%s' % ('_prod' if os.environ.get('ENV') == 'prod' else '')
    client = MongoClient(db_name, 27017)
    db = client.data
    count_gifts = 0
    count_updated = 0
    count_remaining_updated = 0

    # iterate over gifts
    for db_gift in db.gifts.find():
        count_gifts += 1
        new_price = math.floor(db_gift['price'])
        new_remaining_price = math.floor(db_gift['remaining_price'])
        #    print(f'Remaining price would update from {remaining_price} to 0')
        #else:
        #    print(f'Ignoring price {remaining_price} with {remaining_price > 0.0} and {remaining_price < 1.0}')

        if not dry_run:
            count_remaining_updated += 1
            db.gifts.update_one({"_id": ObjectId(db_gift["_id"])}, {
                "$set": {"remaining_price": new_remaining_price}
            })

            db.gifts.update_one({"_id": ObjectId(db_gift["_id"])}, {
                "$set": {"price": new_price}
            })
            count_updated += 1

        else:
            #print(f'would update {db_gift["_id"]} current price {db_gift["price"]} with price {new_price}')
            print(f'would also update remaining price {db_gift["remaining_price"]} to {new_remaining_price}')
    print(f'gifts {count_gifts} / updated {count_updated} / remaining price updated {count_remaining_updated}')

# python3 migrate_prices.py 1
# python3 migrate_prices.py 0
if __name__ == '__main__':
    dry_run = True
    if len(sys.argv) > 1:
        dry_run = bool(int(sys.argv[1]))

    print(f'Running with dry_run={dry_run}')
    migrate(dry_run)
