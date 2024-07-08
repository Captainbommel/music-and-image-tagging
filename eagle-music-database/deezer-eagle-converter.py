import json
import requests
from time import sleep
from dotenv import load_dotenv
import os

# Load the environment variables
load_dotenv()
PROJECT_PATH = os.getenv('PROJECT_PATH')
DEEZER_USER_ID = os.getenv('DEEZER_USER_ID')

def get_user_playlists(user_id):
    '''Returns a list of all of the Deezer users playlists.'''
    user_playlists = f"https://api.deezer.com/user/{user_id}/playlists"

    response = requests.get(user_playlists)
    playlist_data = response.json()

    playlist_titles = []
    playlist_track_links = []
    offset = 0
    for i in range(playlist_data["total"]):
        playlist_titles.append(playlist_data["data"][i+offset]["title"])
        playlist_track_links.append(playlist_data["data"][i+offset]["tracklist"])
        if i+offset == 24:
            playlist_data = requests.get(playlist_data["next"]).json()
            offset -= 25

    return playlist_titles, playlist_track_links


def find_double(title, artist):
    '''Checks if a track is already in the Eagle database and returns the tags and id.'''
    name = remove_non_file_chars(f"{title} - {artist}")
    url = f"http://localhost:41595/api/item/list?name={name}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        print('Error:', response.status_code)
        return [], ""
    if len(data["data"]) == 0:
        return [], ""

    return data["data"][0]["tags"], data["data"][0]["id"]


def update_tags(id, tags):
    '''Updates the Eagle tags of a track.'''
    data = {
        "id": id,
        "tags": list(set(tags)),
    }
    url = "http://localhost:41595/api/item/update"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        print('Error:', response.status_code)


def remove_non_file_chars(name):
    '''Replaces characters wich can't be in a filenames with similar ones.'''
    find =    ["\"", ":", "/", "???", "?", "<", ">", "*", "|"]
    replace = ["⧵", "׃", "／", "unknown artist", "", "ᐸ", "ᐳ", "⚹", "⎟"]  
    
    name = name.strip()
    for i in range(len(find)):
        name = name.replace(find[i], replace[i])
    
    return name


def add_to_eagle(image_path, title, artist, audio_link, tags, id):
    '''Adds a track to the Eagle music database.'''
    data = {
        "url": image_path,
        "name": remove_non_file_chars(f"{title} - {artist}"),
        "website": audio_link,
        "tags": tags,
        "annotation": f"{id}",
    }
    url = "http://localhost:41595/api/item/addFromURL"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        print('Error:', response.status_code)


def add_mp3_to_eagle(title, artist, audio_link, tags, id):
    '''Adds an mp3 track to the Eagle music database.'''
    data = {
        "path": "C:{PROJECT_PATH}/deezer-eagle-converter/mp3.jpg",
        "name": remove_non_file_chars(f"{title} - {artist}"),
        "website": audio_link,
        "tags": tags,
        "annotation": f"{id}",
    }
    url = "http://localhost:41595/api/item/addFromPath"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        print('Error:', response.status_code)


def add_playlist_to_eagle(playlist_title, tracks_link):
    '''
    Adds all tracks of a playlist to the Eagle music database with the playlist name as a tag. 
    If a track is already in the database, only the tag will be added.
    '''
    response = requests.get(tracks_link)
    tracks = response.json()

    offset = 0
    for i in range(tracks["total"]):

        # check for doubles and update tags
        tags, id = find_double(tracks["data"][i+offset]["title"], 
                        tracks["data"][i+offset]["artist"]["name"])
        
        if id != "":
            update_tags(id, tags+[playlist_title])
        else:
            tags = [playlist_title]
            if tracks["data"][i+offset]["id"] < 0:
                add_mp3_to_eagle(title    = tracks["data"][i+offset]["title"], 
                            artist        = tracks["data"][i+offset]["artist"]["name"], 
                            audio_link    = tracks["data"][i+offset]["link"], 
                            tags          = tags,
                            id            = tracks["data"][i+offset]["id"])
            else:
                add_to_eagle(image_path   = tracks["data"][i+offset]["album"]["cover_big"],
                            title         = tracks["data"][i+offset]["title"], 
                            artist        = tracks["data"][i+offset]["artist"]["name"], 
                            audio_link    = tracks["data"][i+offset]["link"], 
                            tags          = tags,
                            id            = tracks["data"][i+offset]["id"])
        
        if i+offset == 24:
            sleep(0.1)
            tracks = requests.get(tracks["next"]).json()
            offset -= 25


########
# Main #
########

# get all playlists of user
user_id = DEEZER_USER_ID
playlist_titles, playlist_tracks = get_user_playlists(user_id)
print(f"Gefundene Playlists: {playlist_titles}")

# add all tracks of each playlist to the Eagle music database
print("Füge Playlists zu Eagle hinzu...")
for i in range(len(playlist_titles)):
    print(f"{i+1}/{len(playlist_titles)} {playlist_titles[i]}")
    add_playlist_to_eagle(playlist_titles[i], playlist_tracks[i])