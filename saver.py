import pymongo

# keep import of main removed to avoid circular import

uri = "mongodb://localhost:27017/"
client = pymongo.MongoClient(uri)
database = client["TGbot"]
collection = database["Weather-Collection"]
users_collection = database["Users"]


def save_user(user_id, username, full_name,city,state,long,lati,time):
    the_document = {
        'user_id': int(user_id),
        'username': username or '',
        'full_name': full_name or '',
        'time': time,
        'city': city,
        'state': state,
        'longitude': long,
        'latitude': lati
    }
    users_collection.update_one({'user_id': the_document['user_id']}, {'$set': the_document}, upsert=True)  
    return 'success'



def get_all_users():
    """Return list of all saved users with user_id, username and full_name."""
    docs = list(users_collection.find({}, {'_id': 0, 'user_id': 1, 'username': 1, 'full_name': 1}))
    return docs


def get_user_location(user_id):
    """Retrieve user's saved location from MongoDB by user_id.
    Returns a dict with lat, lon, display_name, state, country_code if found, else None."""
    user_doc = users_collection.find_one({'user_id': int(user_id)})
    if user_doc and user_doc.get('latitude') and user_doc.get('longitude'):
        return {
            'lat': user_doc.get('latitude'),
            'lon': user_doc.get('longitude'),
            'display_name': user_doc.get('city', ''),
            'state': user_doc.get('state', ''),
            'country_code': user_doc.get('country_code', '')
        }
    return None
