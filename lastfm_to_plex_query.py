# Gets all playcount stats and last played info from LastFM.  Builds a series of sql UPDATE statements that can be used to update
# the plex DB.  You will find the update statements in the generated temp.txt file.

import requests
import collections
import datetime

API_KEY = "your_api_key"
USER = "your_username"

# Your Music Library Section ID
# This can be found by looking at the library_sections table of your Plex DB.
library_section_id = 3

data = {}

f = open('temp.txt', 'w')

# These are the API parameters for our scraping requests.
per_page = 200
api_url_count = 'http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user=%s&api_key=%s&format=json&page=%s&limit=%s'
api_url_recent = 'http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=%s&api_key=%s&format=json&page=%s&limit=%s'

def top_tracks(user, api_key, page, limit):
    """Get the most recent tracks from `user` using `api_key`. Start at page `page` and limit results to `limit`."""
    return requests.get(api_url_count % (user, api_key, page, limit)).json()

def recent_tracks(user, api_key, page, limit):
    """Get the most recent tracks from `user` using `api_key`. Start at page `page` and limit results to `limit`."""
    return requests.get(api_url_recent % (user, api_key, page, limit)).json()

def flatten(d, parent_key=''):
    """From http://stackoverflow.com/a/6027615/254187. Modified to strip # symbols from dict keys."""
    items = []
    for k, v in d.items():
        new_key = parent_key + '_' + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key).items())
        else:
            new_key = new_key.replace('#', '')  # Strip pound symbols from column names
            items.append((new_key, v))
    return dict(items)

def process_track(track):
    """Removes `image` keys from track data. Replaces empty strings for values with None."""
    if 'image' in track:
        del track['image']
    flattened = flatten(track)
    for key, val in flattened.iteritems():
        if val == '':
            flattened[key] = None
    return flattened

def build_statement(title, playcount, date):
    try:
        f.write("UPDATE metadata_item_settings " + "SET view_count=" + playcount + " WHERE guid IN (SELECT guid FROM metadata_items WHERE library_section_id = " + library_section_id + " AND metadata_type = 10 AND UPPER(title) = UPPER(\""+ title.replace('\"','\"\"') + "\"));\n");
    except:
        pass

def get_date(time):
    return datetime.datetime.fromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S')

# For playcount
# We need to get the first page so we can find out how many total pages there are in our listening history.
resp = top_tracks(USER, API_KEY, 1, 200)
total_pages = int(resp['toptracks']['@attr']['totalPages'])

all_pages = []
for page_num in xrange(1, total_pages + 1):
    # print 'Page', page_num, 'of', total_pages
    page = top_tracks(USER, API_KEY, page_num, 200)
    all_pages.append(page)

# Iterate through all pages
num_pages = len(all_pages)
for page_num, page in enumerate(all_pages):
    print 'Page', page_num + 1, 'of', num_pages
    # On each page, iterate through all tracks
    for track in page['toptracks']['track']:
        # Process each track and insert it into the `tracks` table
        track_data = process_track(track);
        data[track_data['name']] = [track_data['playcount'], 0]

# For recent played
resp = recent_tracks(USER, API_KEY, 1, 200)
total_pages = int(resp['recenttracks']['@attr']['totalPages'])

all_pages = []
for page_num in xrange(1, total_pages + 1):
    # print 'Page', page_num, 'of', total_pages
    page = recent_tracks(USER, API_KEY, page_num, 200)
    all_pages.append(page)

num_pages = len(all_pages)
for page_num, page in enumerate(all_pages):
    # print 'Page', page_num + 1, 'of', num_pages
    # On each page, iterate through all tracks
    for track in page['recenttracks']['track']:
        # Process each track and insert it into the `tracks` table
        track_data = process_track(track);

        try:
            name = track_data['name']
            date = track_data['date_uts']

            if data.has_key(name):
                if(data[name][1] < date):
                    data[name][1] = date
            else:
                data[name] = [1, date]
        except:
            print track_data

for key, value in data.iteritems():
    build_statement(key, value[0], value[1])
