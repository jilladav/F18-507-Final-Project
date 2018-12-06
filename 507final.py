import spotipy
import spotipy.util as util	
import spotipy.oauth2 as oauth2
import requests
import json
from requests_oauthlib import OAuth1
import sys
import sqlite3
import secret_data

client_id='4a1b1a7008b94b70a7f9d8ef4b3569b6'
client_secret='446930c0645144f386a40dd71d8130d0'
DBNAME = 'music.db'
consumer_key = secret_data.CONSUMER_KEY
consumer_secret = secret_data.CONSUMER_SECRET
access_token = secret_data.ACCESS_KEY
access_secret = secret_data.ACCESS_SECRET

last_fm_token = "677c8aff7b951e74d376e974ca22d1fa"
last_fm_secret = "646464594f4e6e49a6e73279e522d0e5"

url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
requests.get(url, auth=auth)

credentials = oauth2.SpotifyClientCredentials(client_id=client_id,client_secret=client_secret)
token = credentials.get_access_token()
spotify = spotipy.Spotify(auth=token)

id_list = []

class Artist:
	def __init__(self, id=0, name="None", genre="None", top_songs=[], followers=0, json=None):
		if json is None:
			self.id = id
			self.name = name
			self.genre = genre
			self.top_songs = top_songs
			self.followers = followers
		else:
			self.process_json_dict(json)

	def process_json_dict(self,json):
		self.id = json['id']
		self.name = json['name']
		self.genre = json['genres'][0]
		self.top_songs = self.get_top_tracks(self.id)
		self.get_twitter_data(self.name)

	def get_top_tracks(self, id):
		results = make_request_using_cache_spotify_songs(id)
		songs = []
		if len(results) >= 5:
			for x in range(0,5):
				json = results[x]
				song = Song(json=json)
				songs.append(song)
				update_songs(song)
		else:
			for x in range(0,len(results)):
				json = results[x]
				song = Song(json=json)
				songs.append(song)
				update_songs(song)
		if len(songs) < 5:
			x = len(songs)
			for item in range(x,5):
				songs.append(None)

		for json in results[5:]:
				song = Song(json=json)
				songs.append(song)
				update_songs(song)

		return songs

	def get_twitter_data(self,name):
		base_url = "https://api.twitter.com/1.1/users/search.json"
		params = {}
		params['q'] = name
		params['count'] = 1
		result = make_request_using_cache_twitter(base_url,params)
		#f = open("tweet.json", "w")
		#f.write(json.dumps(result.text, indent=4))
		#f.close()
		#result = json.loads(result.text)
		self.followers = result[0]["followers_count"]

	def __str__ (self):
		return self.name

class Song:
	def __init__(self, id=0, name="None", artist="None", popularity=0, release="None", tags=[], listeners=0, playcount=0, json=None):
		if json is None:
			self.id = id
			self.name = name
			self.artist = artist
			self.popularity = popularity
			self.release = release
			self.tags = tags
			self.listeners = listeners
			self.playcount = playcount
		else:
			self.process_json_dict(json)

	def process_json_dict(self,json):
		self.id = json['id']
		self.name = json['name']
		self.artist = json['artists'][0]['name']
		self.popularity = json['popularity']
		self.release = json['album']['release_date']
		self.tags = []
		self.listeners = 0
		self.playcount = 0
		self.get_last_fm_data(name=self.name,artist=self.artist)

	def get_last_fm_data(self,name,artist):
		base_url = 'http://ws.audioscrobbler.com/2.0/'
		params = {}
		params['artist'] = artist
		params['track'] = name
		params['method'] = "track.getInfo"
		params['format'] = "json"
		params['api_key'] = last_fm_token
		result = make_request_using_cache_last_fm(base_url, params)
		self.listeners = result['track']['listeners']
		self.playcount = result['track']['playcount']
		tags = result['track']['toptags']['tag']
		tag_list = []
		for tag in tags:
			self.tags.append(tag['name'])


	def __str__ (self):
		return self.name

def create_artists():
	try:
		conn = sqlite3.connect(DBNAME)
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	try:
		statement = '''
            DROP TABLE IF EXISTS 'Artists';
        '''
		cur.execute(statement)
		statement = '''CREATE TABLE 'Artists' 
        ('Id' TEXT PRIMARY KEY, 'Name' Text, 'PrimaryGenre' TEXT, 'TopSong1Id' TEXT,
            'TopSong2Id' TEXT, 'TopSong3Id' TEXT, 'TopSong4Id' TEXT, 'TopSong5Id' TEXT, 'Followers' INT);'''
		cur.execute(statement)

		conn.commit()
		conn.close()
    
	except:
		print("Could not create table Artists.")

def update_artists(artist):
	conn = sqlite3.connect(DBNAME)
	cur = conn.cursor()

	'''if len(artist.top_songs) < 5:
		statement = "INSERT INTO 'Artists' (Id, Name, PrimaryGenre, TopSong1Id, TopSong2Id, TopSong3Id, TopSong4Id,
		TopSong5Id, Followers) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
		cur.execute(statement, (artist.id, artist.name, artist.genre, 'NULL', 'NULL', 'NULL', 'NULL', 'NULL', artist.followers))'''

	song_names = []
	for song in artist.top_songs:
		if song is None:
			song_names.append("NULL")
		else:
			song_names.append(song.name)
	
	statement = "INSERT INTO 'Artists' (Id, Name, PrimaryGenre, TopSong1Id, TopSong2Id, TopSong3Id, TopSong4Id, TopSong5Id, Followers) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
	cur.execute(statement, (artist.id, artist.name, artist.genre, song_names[0], song_names[1], song_names[2], song_names[3], song_names[4], artist.followers))

	conn.commit()
	conn.close()

def create_songs():
	try:
		conn = sqlite3.connect(DBNAME)
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	try:
		statement = '''DROP TABLE IF EXISTS 'Songs';'''
		cur.execute(statement)
		statement = '''CREATE TABLE 'Songs' ('Id' TEXT PRIMARY KEY, 'Name' Text, 'ArtistId' TEXT, 'Popularity' INT, 'ReleaseDate' TEXT, 'Listeners' INT, 'PlayCount' INT, 'Tag1' TEXT, 'Tag2' TEXT, 'Tag3' TEXT, 'Tag4' TEXT, 'Tag5' TEXT);'''
		cur.execute(statement)

		conn.commit()
		conn.close()
    
	except:
		print("Could not create table Songs.")

def update_songs(song):
	conn = sqlite3.connect(DBNAME)
	cur = conn.cursor()
	if len(song.tags) < 5:
		statement = "INSERT OR IGNORE INTO 'Songs' (Id, Name, ArtistId, Popularity, ReleaseDate, Listeners, PlayCount, Tag1, Tag2, Tag3, Tag4, Tag5) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
		cur.execute(statement, (song.id, song.name, song.artist, song.popularity, song.release, song.listeners, song.playcount, 'NULL', 'NULL', 'NULL', 'NULL', 'NULL'))

	else:
		statement = "INSERT OR IGNORE INTO 'Songs' (Id, Name, ArtistId, Popularity, ReleaseDate, Listeners, PlayCount, Tag1, Tag2, Tag3, Tag4, Tag5) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
		cur.execute(statement, (song.id, song.name, song.artist, song.popularity, song.release, song.listeners, song.playcount, song.tags[0], song.tags[1], song.tags[2], song.tags[3], song.tags[4]))

	conn.commit()
	conn.close()

def connect_songs_artists(artist):
	conn = sqlite3.connect(DBNAME)
	cur = conn.cursor()

	artist_id = cur.execute("SELECT id FROM 'Artists' WHERE Name=?", (artist.name,)).fetchone()[0]
	statement = "UPDATE Songs SET ArtistId = ? WHERE ArtistId = ?"
	cur.execute(statement,(artist_id, artist.name))

	#I feel like there's a cleaner way to do this...
	for song in artist.top_songs:
		if song != None:
			song_id = cur.execute("SELECT id FROM 'Songs' WHERE Name=?", (song.name,)).fetchone()[0]
			statement = "UPDATE Artists SET TopSong1Id = ? WHERE TopSong1Id = ?"
			cur.execute(statement,(song_id, song.name))
			statement = "UPDATE Artists SET TopSong2Id = ? WHERE TopSong2Id = ?"
			cur.execute(statement,(song_id, song.name))
			statement = "UPDATE Artists SET TopSong3Id = ? WHERE TopSong3Id = ?"
			cur.execute(statement,(song_id, song.name))
			statement = "UPDATE Artists SET TopSong4Id = ? WHERE TopSong4Id = ?"
			cur.execute(statement,(song_id, song.name))
			statement = "UPDATE Artists SET TopSong5Id = ? WHERE TopSong5Id = ?"
			cur.execute(statement,(song_id, song.name))

	conn.commit()
	conn.close()

#CACHE_DICTION_SPOTIFY = {}
CACHE_FNAME_SPOTIFY = 'spotify_cache.json'
try:
    cache_file = open(CACHE_FNAME_SPOTIFY, 'r')
    cache_contents = cache_file.read()
    CACHE_DICTION_SPOTIFY = json.loads(cache_contents)
    cache_file.close()

except:
    CACHE_DICTION_SPOTIFY = {}

'''def params_unique_combination_spotify(name): 
	alphabetized_keys = sorted(params.keys()) 
	res = []
	for k in alphabetized_keys: 
		res.append("{}-{}".format(k, params[k]))
	return baseurl +"_"+"_".join(res)'''

def make_request_using_cache_spotify(name): 
	name.replace(" ", "_")
	unique_ident = name

	if unique_ident in CACHE_DICTION_SPOTIFY: 
		print("Getting cached data...")
		return CACHE_DICTION_SPOTIFY[unique_ident]

	else: 
		print("Making a request for new data...")

		'''credentials = oauth2.SpotifyClientCredentials(client_id=client_id,client_secret=client_secret)
		token = credentials.get_access_token()
		spotify = spotipy.Spotify(auth=token)'''
		results = spotify.search(q='artist:' + name, type='artist')
		#resp = requests.get(baseurl, params, auth=auth) 
		try:
			CACHE_DICTION_SPOTIFY[unique_ident] = results['artists']['items'][0]
			dumped_json_cache = json.dumps(CACHE_DICTION_SPOTIFY) 
			fw = open(CACHE_FNAME_SPOTIFY,"w") 
			fw.write(dumped_json_cache) 
			fw.close()
		except:
			return

		return CACHE_DICTION_SPOTIFY[unique_ident]

CACHE_FNAME_SPOTIFY = 'spotify_cache.json'
try:
    cache_file = open(CACHE_FNAME_SPOTIFY, 'r')
    cache_contents = cache_file.read()
    CACHE_DICTION_SPOTIFY = json.loads(cache_contents)
    cache_file.close()

except:
    CACHE_DICTION_SPOTIFY = {}

def make_request_using_cache_spotify_songs(id): 
	unique_ident = id + "songs"

	if unique_ident in CACHE_DICTION_SPOTIFY: 
		print("Getting cached data...")
		return CACHE_DICTION_SPOTIFY[unique_ident]

	else: 
		print("Making a request for new data...")
		results = spotify.artist_top_tracks(id)
		#resp = requests.get(baseurl, params, auth=auth) 
		try:
			CACHE_DICTION_SPOTIFY[unique_ident] = results['tracks']
			dumped_json_cache = json.dumps(CACHE_DICTION_SPOTIFY) 
			fw = open(CACHE_FNAME_SPOTIFY,"w") 
			fw.write(dumped_json_cache) 
			fw.close()
		except:
			return

		return CACHE_DICTION_SPOTIFY[unique_ident]


CACHE_FNAME_TWITTER = 'twitter_cache.json'
try:
    cache_file = open(CACHE_FNAME_TWITTER, 'r')
    cache_contents = cache_file.read()
    CACHE_DICTION_TWITTER = json.loads(cache_contents)
    cache_file.close()

except:
    CACHE_DICTION_TWITTER = {}

def params_unique_combination(baseurl, params): 
	alphabetized_keys = sorted(params.keys()) 
	res = []
	for k in alphabetized_keys: 
		res.append("{}-{}".format(k, params[k]))
	return baseurl +"_"+"_".join(res)

def make_request_using_cache_twitter(baseurl, params): 
	params['q'].replace(" ", "_")
	unique_ident = params_unique_combination(baseurl,params)

	if unique_ident in CACHE_DICTION_TWITTER: 
		print("Getting cached data...")
		return CACHE_DICTION_TWITTER[unique_ident]

	else: 
		print("Making a request for new data...")

		resp = requests.get(baseurl, params, auth=auth) 
		CACHE_DICTION_TWITTER[unique_ident] = json.loads(resp.text) 
		dumped_json_cache = json.dumps(CACHE_DICTION_TWITTER) 
		fw = open(CACHE_FNAME_TWITTER,"w") 
		fw.write(dumped_json_cache) 
		fw.close()

		return CACHE_DICTION_TWITTER[unique_ident]


CACHE_FNAME_LAST_FM = 'last_fm_cache.json'
try:
    cache_file = open(CACHE_FNAME_LAST_FM, 'r')
    cache_contents = cache_file.read()
    CACHE_DICTION_LAST_FM = json.loads(cache_contents)
    cache_file.close()

except:
    CACHE_DICTION_LAST_FM = {}


def make_request_using_cache_last_fm(baseurl, params): 
	unique_ident = params_unique_combination(baseurl,params)
	
	if unique_ident in CACHE_DICTION_LAST_FM: 
		print("Getting cached data...")
		return CACHE_DICTION_LAST_FM[unique_ident]

	else: 
		print("Making a request for new data...")

		resp = requests.get(baseurl, params) 
		CACHE_DICTION_LAST_FM[unique_ident] = json.loads(resp.text) 
		dumped_json_cache = json.dumps(CACHE_DICTION_LAST_FM) 
		fw = open(CACHE_FNAME_LAST_FM,"w") 
		fw.write(dumped_json_cache) 
		fw.close()

		return CACHE_DICTION_LAST_FM[unique_ident]

def search_for_artist(name,id_list):
	artist = make_request_using_cache_spotify(name)
	artist_object = Artist(json=artist)

	if artist_object.id != 0 and artist_object.id not in id_list:
		update_artists(artist_object)
		connect_songs_artists(artist_object)

	return artist_object

def get_related_artists(id):
	related = spotify.artist_related_artists(id)
	for artist in related['artists']:
		artist_dict = artist
		search_for_artist(artist['name'])

def query_top_songs(name):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	artist = search_for_artist(name)

	statement = '''SELECT Songs.Name, Songs.Popularity, Songs.Listeners, Songs.PlayCount FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ?'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()

	conn.commit()
	conn.close()

def query_release_dates(name):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	artist = search_for_artist(name)

	year = "2017%"

	statement = '''SELECT Songs.Name, Songs.Popularity, Songs.Listeners, Songs.PlayCount FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? AND Songs.ReleaseDate LIKE ?'''
	cur.execute(statement, (artist.id, year))

	lst = cur.fetchall()

	conn.commit()
	conn.close()

def query_tags(name):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	artist = search_for_artist(name)

	year = "2017%"

	#repeat for all tags
	statement = '''SELECT Songs.Name, Songs.Tag1 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag1'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()

	conn.commit()
	conn.close()

#From https://github.com/plamere/spotipy/issues/194
'''credentials = oauth2.SpotifyClientCredentials(client_id=client_id,client_secret=client_secret)
token = credentials.get_access_token()
spotify = spotipy.Spotify(auth=token)
results = spotify.search(q='artist:' + 'Andrew McMahon', type='artist')

artist = results['artists']['items'][0]'''
#print(artist)

create_artists()
create_songs()

#query_release_dates("Andrew McMahon in the Wilderness")
artist = search_for_artist("The Beatles",id_list)
id_list.append(artist.id)

'''artist = make_request_using_cache_spotify("Andrew McMahon")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("The 1975")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("The Chainsmokers")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("Fall Out Boy")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("No Rome")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("Walk The Moon")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

artist = make_request_using_cache_spotify("Grouplove")
artist_object = Artist(json=artist)

update_artists(artist_object)
connect_songs_artists(artist_object)

#related = spotify.artist_related_artists(artist_object.id)

#get_twitter_data(artist_object)
#print(artist_object.followers)'''

'''url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
requests.get(url, auth=auth)'''


#results = spotify.artist_top_tracks(artist)
#print(results['tracks'][3]['album']['release_date'])



'''resp = requests.get(base_url, params)
result = json.loads(resp.text)
result_tag = result['track']['toptags'] 
print(result_tag)'''