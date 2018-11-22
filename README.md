
## Presentation

This small project was made to organize the presents for my family.
Every registered member of the family can add wishes, and can see wishes from other members of the family.
Everyone can then claim a wish to say "I will buy this" and the wish disappear from the "available" list in order to avoid two people buying the same gift.
You can also contribute to a gift without buying it entirely, and the system keeps track of the remaining amount missing from this gift, which can be helpful for group gifts.

[[https://github.com/lcalem/family-presents/blob/master/img/interface.png|alt=interface]]


## How to install

1. Go on your server
2. Clone the repo `git clone git@github.com:lcalem/family-presents.git`
3. `cd` in the repo and build the docker using `make build_nginx`
4. Up the server using `make run_nginx`
5. Up the DB using `make up_db`
6. Go in the db container (`docker exec -it docker_mongo_prod_1 mongo`) and set the active db to "data" (mongo> `use data`)
7. Insert users of your system `db.users.insert({"name": "<DISPLAY_NAME>", "username": "<USERNAME>", "password": "<PASSWORD>"})`

After this procedure the website should be up and running on your server, to make it accessible from a specific URL you own you then need to make a DNS redirection to your server IP.

