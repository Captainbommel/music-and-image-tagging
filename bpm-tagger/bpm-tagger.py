import json
import os
import librosa as rosa
import requests
import os
from dotenv import load_dotenv

# Load the environment variables
load_dotenv()
PROJECT_PATH = os.getenv('PROJECT_PATH')

def get_eagle_and_deezer_ids(limit=1000000):
    '''Gets the ids and urls of all songs in the database.'''
    url = f"http://localhost:41595/api/item/list?limit={limit}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        print('Error:', response.status_code)
        return [], []
    
    l = len(data["data"])
    print(f"Tracks found: {l}")
    eagle_ids = [None] * l
    deezer_ids = [None] * l
    for i in range(l):
        eagle_ids[i] = data["data"][i]["id"]
        deezer_ids[i] = data["data"][i]["annotation"]

    return eagle_ids, deezer_ids

def get_preview_url(id):
    '''Gets the 30 second preview url of a song.'''
    url = f"https://api.deezer.com/track/{id}"
    response = requests.get(url)
    data = response.json()

    if response.status_code != 200:
        print('Error:', response.status_code)
        return ""
    
    return data["preview"]


def download_preview(deezer_id, path):
    '''Downloads the 30 second preview of a song.'''
    url = get_preview_url(deezer_id)
    if url == "":
        print("No preview available.")
        return False
    response = requests.get(url)
    if response.status_code != 200:
        print('Error:', response.status_code)
        return False
    with open(path, 'wb') as f:
        f.write(response.content)
        f.close()
    return True


def get_bpm(path):
    '''Estimates the bpm of a given mp3 file.'''
    y, sr = rosa.load(path)
    tempo, beat_frames = rosa.beat.beat_track(y=y, sr=sr)
    return tempo[0]

def round_to_multiple(number, multiple):
    return multiple * round(number / multiple)


def add_bpm_tag(eagle_id, bpm):
    '''Adds the bpm tag to the track with the given id in the database.'''

    # get the tags of the track
    url = f"http://localhost:41595/api/item/info?id={eagle_id}"
    
    response = requests.get(url)
    data = response.json()
    tags = data["data"]["tags"]

    if response.status_code != 200:
        print('Error:', response.status_code)
        return

    # update the tags
    data = {
        "id": eagle_id,
        "tags": tags + [str(bpm)+"BPM"] if str(bpm)+"BPM" not in tags else tags,
    }
    url = "http://localhost:41595/api/item/update"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        print('Error:', response.status_code)

def add_no_30sec_preview_tag(eagle_id):
    '''Adds the "no 30 second preview" tag to the track with the given id in the database.'''

    # get the tags of the track
    url = f"http://localhost:41595/api/item/info?id={eagle_id}"
    
    response = requests.get(url)
    data = response.json()
    tags = data["data"]["tags"]

    if response.status_code != 200:
        print('Error:', response.status_code)
        return

    # update the tags
    data = {
        "id": eagle_id,
        "tags": tags + ["Geolocked"] if "Geolocked" not in tags else tags,
    }
    url = "http://localhost:41595/api/item/update"
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, data=json.dumps(data), headers=headers)

    if response.status_code != 200:
        print('Error:', response.status_code)


def delete_preview(path):
    '''Deletes the downloaded preview file.'''
    if os.path.exists(path):
        os.remove(path)
        print("Preview file deleted.")
    else:
        print("Preview file does not exist.")



########
# Main #
########

eagle_ids, deezer_ids = get_eagle_and_deezer_ids()

for i in range(len(eagle_ids)):
    deezer_id = deezer_ids[i]
    if int(deezer_id) < 0: 
        continue
    eagle_id = eagle_ids[i]
    path = f"{PROJECT_PATH}/bpm-tagger/deezer-preview-mp3/{eagle_id}_{deezer_id}.mp3"

    if download_preview(deezer_id, path):
        bpm = round_to_multiple(get_bpm(path), 5)
        print(f"Estimated tempo: {bpm} beats per minute")
        add_bpm_tag(eagle_id, bpm)
    else:
        add_no_30sec_preview_tag(eagle_id)

    if i == 10:
        break