import spotipy
import spotipy.util as util	
import spotipy.oauth2 as oauth2
import requests
import json
from requests_oauthlib import OAuth1
import sys
import sqlite3
import secret_data
import plotly
import plotly.plotly as py
import plotly.graph_objs as go

#put API keys in secret file later lol
client_id= secret_data.client_id
client_secret= secret_data.client_secret
DBNAME = 'music.db'
consumer_key = secret_data.CONSUMER_KEY
consumer_secret = secret_data.CONSUMER_SECRET
access_token = secret_data.ACCESS_KEY
access_secret = secret_data.ACCESS_SECRET

last_fm_token = secret_data.last_fm_token
last_fm_secret = secret_data.last_fm_secret

url = 'https://api.twitter.com/1.1/account/verify_credentials.json'
auth = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
requests.get(url, auth=auth)

credentials = oauth2.SpotifyClientCredentials(client_id=client_id,client_secret=client_secret)
token = credentials.get_access_token()
spotify = spotipy.Spotify(auth=token)


#NOTE: Maybe get more tracks for each artist by using last.fm and then creating a Song object, updating DB, etc. with that
#Use last.fm to get a list
#Use Spotify Search to get IDs using names from the list
#Use Spotify get track to get information

class Artist:
	def __init__(self, id=0, name="None", genre="None", top_songs=[], followers=0, popularity=0, json=None):
		if json is None:
			self.id = id
			self.name = name
			self.genre = genre
			self.top_songs = top_songs
			self.followers = followers
			self.popularity = popularity
		else:
			self.process_json_dict(json)

	def process_json_dict(self,json):
		self.id = json['id']
		self.name = json['name']
		self.genre = json['genres'][0]
		self.popularity = json['popularity'] 
		self.top_songs = self.get_top_tracks(self.id)
		self.get_twitter_data(self.name)

	def get_top_tracks(self, id):
		results = make_request_using_cache_spotify_songs(id)
		songs = []
		song_names = []
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

		for song in songs:
			song_names.append(song.name)

		more = self.get_last_fm_songs(self.name)
		more_songs = more['toptracks']['track']

		for json in more_songs:
			if json['name'] not in song_names:
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

	def get_last_fm_songs(self,name):
		base_url = 'http://ws.audioscrobbler.com/2.0/'
		params = {}
		params['artist'] = name
		params['limit'] = 100
		params['method'] = "artist.getTopTracks"
		params['format'] = "json"
		params['api_key'] = last_fm_token
		result = make_request_using_cache_last_fm(base_url, params)

		return(result)

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
		try:
			self.name = json['name']
			self.id = json['id']
			self.artist = json['artists'][0]['name']
			self.popularity = json['popularity']
			self.release = json['album']['release_date']
			self.tags = []
			self.listeners = 0
			self.playcount = 0
			self.get_last_fm_data(name=self.name,artist=self.artist)
		except:
			try:
				#TODO: Add this to cache
				results = spotify.search(q='track:' + self.name, type='track')
				json = results['tracks']['items'][0]
				self.process_json_dict(json=json)
			except:
				self.name = json['name']
				self.id = 0
				self.artist = "Unknown"
				self.tags = []
				self.release = "Unknown"
				self.popularity = 0
				self.listeners = 0
				self.playcount = 0
				return

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
            'TopSong2Id' TEXT, 'TopSong3Id' TEXT, 'TopSong4Id' TEXT, 'TopSong5Id' TEXT, 'Popularity' INT, 'TwitterFollowers' INT);'''
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
	
	statement = "INSERT INTO 'Artists' (Id, Name, PrimaryGenre, TopSong1Id, TopSong2Id, TopSong3Id, TopSong4Id, TopSong5Id, Popularity, TwitterFollowers) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
	cur.execute(statement, (artist.id, artist.name, artist.genre, song_names[0], song_names[1], song_names[2], song_names[3], song_names[4], artist.popularity, artist.followers))

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
			try:
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
			except:
				continue

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

def search_for_artist(name):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")
	
	artist = make_request_using_cache_spotify(name)
	artist_object = Artist(json=artist)

	'''statement = '''SELECT Id from ARTISTS'''
	cur.execute(statement)

	id_list = []
	lst = cur.fetchall()
	for row in lst:
		id_list.append(row[0])'''

	#if artist_object.id != 0 and artist_object.id not in id_list:
	update_artists(artist_object)
	connect_songs_artists(artist_object)

	conn.commit()
	conn.close()

	return artist_object

def get_related_artists(id):
	#Do I need to cache this related artists search??? Maybe?
	related = spotify.artist_related_artists(id)
	related_artists = []
	for artist in related['artists']:
		artist_dict = artist
		related_artist = search_for_artist(artist['name'])
		related_artists.append(related_artist)

	return related_artists

def query_top_songs(name, metric):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	metric=metric

	artist = search_for_artist(name)

	popularity_dict = {}
	listeners_dict = {}
	playcount_dict = {}
	name_list = []

	statement = '''SELECT Songs.Name, Songs.Popularity, Songs.Listeners, Songs.PlayCount FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ?'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()

	for row in lst:
		popularity_dict[row[0]] = row[1]
		listeners_dict[row[0]] = (row[2] / 1000)
		playcount_dict[row[0]] = (row[3] / 1000)
		name_list.append(row[0])

	graph_song_popularity(popularity_dict, listeners_dict, playcount_dict, name_list, metric)

	conn.commit()
	conn.close()

def query_release_dates(name, year1, year2):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	artist = search_for_artist(name)

	#See if you can make this work with the last.fm stuff too

	date_dict = {}
	year1_list = []
	year2_list = []
	year1_total_popularity = 0
	year2_total_popularity = 0

	statement = '''SELECT Songs.Popularity, Songs.Listeners, Songs.PlayCount FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? AND Songs.ReleaseDate LIKE ?'''
	cur.execute(statement, (artist.id, "%" + str(year1) + "%"))

	lst = cur.fetchall()

	for row in lst:
		popularity = row[0]
		year1_list.append(popularity)
		year1_total_popularity += popularity


	statement = '''SELECT Songs.Popularity, Songs.Listeners, Songs.PlayCount FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? AND Songs.ReleaseDate LIKE ?'''
	cur.execute(statement, (artist.id, "%" + str(year2) + "%"))

	lst = cur.fetchall()

	for row in lst:
		popularity = row[0]
		year2_list.append(popularity)
		year2_total_popularity += popularity

	date_dict[year1] = year1_total_popularity / len(year1_list)
	date_dict[year2] = year2_total_popularity / len(year2_list)

	graph_year_popularity(date_dict, year1, year2)

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

	tag_dict = {}

	#repeat for all tags
	statement = '''SELECT COUNT(*), Songs.Tag1 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag1'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()
	for row in lst:
		if row[1] != "NULL":
			tag_dict[row[1]] = row[0]

	statement = '''SELECT COUNT(*), Songs.Tag2 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag2'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()
	for row in lst:
		if row[1] not in tag_dict.keys():
			if row[1] != "NULL":
				tag_dict[row[1]] = row[0]
		else:
			tag_dict[row[1]] += row[0]

	statement = '''SELECT COUNT(*), Songs.Tag3 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag3'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()
	for row in lst:
		if row[1] not in tag_dict.keys():
			if row[1] != "NULL":
				tag_dict[row[1]] = row[0]
		else:
			tag_dict[row[1]] += row[0]


	statement = '''SELECT COUNT(*), Songs.Tag4 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag4'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()
	for row in lst:
		if row[1] not in tag_dict.keys():
			if row[1] != "NULL":
				tag_dict[row[1]] = row[0]
		else:
			tag_dict[row[1]] += row[0]


	statement = '''SELECT COUNT(*), Songs.Tag5 FROM Songs JOIN Artists ON
	Songs.ArtistId = Artists.Id WHERE Artists.Id = ? GROUP BY Tag5'''
	cur.execute(statement, (artist.id,))

	lst = cur.fetchall()
	for row in lst:
		if row[1] not in tag_dict.keys():
			if row[1] != "NULL":
				tag_dict[row[1]] = row[0]
		else:
			tag_dict[row[1]] += row[0]

	graph_tags(tag_dict)

	conn.commit()
	conn.close()

def query_related_artists(name,metric):
	try:
		conn = sqlite3.connect(DBNAME)
        #From https://stackoverflow.com/questions/3425320/sqlite3-programmingerror-you-must-not-use-8-bit-bytestrings-unless-you-use-a-te
		conn.text_factory = str
		cur = conn.cursor()
	except:
		print("Could not connect to database.")

	metric=metric

	artist_obj = search_for_artist(name)

	related_artists = get_related_artists(artist_obj.id)

	artist_pop_dict = {}
	artist_follower_dict = {}
	name_list = []

	for artist in related_artists:
		statement = '''SELECT Artists.Name, Artists.Popularity, Artists.TwitterFollowers FROM Artists WHERE Artists.Id = ?'''
		cur.execute(statement, (artist.id,))

		try:
			lst = cur.fetchone()
			#for row in lst:
				#print(row[0])
			artist_pop_dict[lst[0]] = lst[1]
			artist_follower_dict[lst[0]] = lst[2] / 1000
			name_list.append(lst[0])
		except:
			continue

	graph_related_artists(artist_pop_dict,artist_follower_dict,artist_obj,name_list,metric)

	conn.commit()
	conn.close()

def graph_song_popularity(pop_dict, list_dict, play_dict, name_list, metric):	
	'''trace1 = go.Bar(
    x=[name_list[0], name_list[1], name_list[2], name_list[3], name_list[4]],
    y=[pop_dict[name_list[0]], pop_dict[name_list[1]], pop_dict[name_list[2]], pop_dict[name_list[3]], pop_dict[name_list[4]]],
    name='Spotify Popularity'
	)

	trace2 = go.Bar(
    x=[name_list[0], name_list[1], name_list[2], name_list[3], name_list[4]],
    y=[list_dict[name_list[0]], list_dict[name_list[1]], list_dict[name_list[2]], list_dict[name_list[3]], list_dict[name_list[4]]],
    name='last.fm Listeners (in thousands)'
	)

	trace3 = go.Bar(
    x=[name_list[0], name_list[1], name_list[2], name_list[3], name_list[4]],
    y=[play_dict[name_list[0]], play_dict[name_list[1]], play_dict[name_list[2]], play_dict[name_list[3]], play_dict[name_list[4]]],
    name='last.fm Playcount (in thousands)'
	)

	data = [trace1, trace2, trace3]
	layout = go.Layout(
    barmode='group'
	)

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='grouped-bar')'''

	'''trace1 = go.Bar(
    x=['Spotify Popularity', 'last.fm Listeners (in thousands)', 'last.fm Playcount (in thousands)'],
    y=[pop_dict[name_list[0]], list_dict[name_list[0]], play_dict[name_list[0]]],
    name = name_list[0]
	)

	trace2 = go.Bar(
    x=['Spotify Popularity', 'last.fm Listeners (in thousands)', 'last.fm Playcount (in thousands)'],
    y=[pop_dict[name_list[1]], list_dict[name_list[1]], play_dict[name_list[1]]],
    name = name_list[1]
	)

	trace3 = go.Bar(
    x=['Spotify Popularity', 'last.fm Listeners (in thousands)', 'last.fm Playcount (in thousands)'],
    y=[pop_dict[name_list[2]], list_dict[name_list[2]], play_dict[name_list[2]]],
    name = name_list[2]
	)

	trace4 = go.Bar(
    x=['Spotify Popularity', 'last.fm Listeners (in thousands)', 'last.fm Playcount (in thousands)'],
    y=[pop_dict[name_list[3]], list_dict[name_list[3]], play_dict[name_list[3]]],
    name = name_list[3]
	)

	trace5 = go.Bar(
    x=['Spotify Popularity', 'last.fm Listeners (in thousands)', 'last.fm Playcount (in thousands)'],
    y=[pop_dict[name_list[4]], list_dict[name_list[4]], play_dict[name_list[4]]],
    name = name_list[4]
	)

	data = [trace1, trace2, trace3, trace4, trace5]
	layout = go.Layout(
		barmode='group',
    	autosize=False,
    	width=700,
    	height=700,
    	margin=go.layout.Margin(
        l=50,
        r=50,
        b=150,
        t=100,
        pad=4),
    )

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='grouped-bar')'''

	if metric == "spotify":
		trace1 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[pop_dict[name_list[0]]],
	    name = name_list[0]
		)

		trace2 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[pop_dict[name_list[1]]],
	    name = name_list[1]
		)

		trace3 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[pop_dict[name_list[2]]],
	    name = name_list[2]
		)

		trace4 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[pop_dict[name_list[3]]],
	    name = name_list[3]
		)

		trace5 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[pop_dict[name_list[4]]],
	    name = name_list[4]
		)

		data = [trace1, trace2, trace3, trace4, trace5]
		layout = go.Layout(
			barmode='group',
	    	autosize=False,
	    	width=700,
	    	height=700,
	    	margin=go.layout.Margin(
	        l=50,
	        r=50,
	        b=150,
	        t=100,
	        pad=4),
	    )

		fig = go.Figure(data=data, layout=layout)
		py.plot(fig, filename='grouped-bar')

	elif metric == "listeners":
		trace1 = go.Bar(
	    x=['last.fm Listeners (in thousands)'],
	    y=[list_dict[name_list[0]]],
	    name = name_list[0]
		)

		trace2 = go.Bar(
	    x=['last.fm Listeners (in thousands)'],
	    y=[list_dict[name_list[1]]],
	    name = name_list[1]
		)

		trace3 = go.Bar(
	    x=['last.fm Listeners (in thousands)'],
	    y=[list_dict[name_list[2]]],
	    name = name_list[2]
		)

		trace4 = go.Bar(
	    x=['last.fm Listeners (in thousands)'],
	    y=[list_dict[name_list[3]]],
	    name = name_list[3]
		)

		trace5 = go.Bar(
	    x=['last.fm Listeners (in thousands)'],
	    y=[list_dict[name_list[4]]],
	    name = name_list[4]
		)

		data = [trace1, trace2, trace3, trace4, trace5]
		layout = go.Layout(
			barmode='group',
	    	autosize=False,
	    	width=700,
	    	height=700,
	    	margin=go.layout.Margin(
	        l=50,
	        r=50,
	        b=150,
	        t=100,
	        pad=4),
	    )

		fig = go.Figure(data=data, layout=layout)
		py.plot(fig, filename='grouped-bar')

	elif metric == "playcount":
		trace1 = go.Bar(
	    x=['last.fm Playcount (in thousands)'],
	    y=[play_dict[name_list[0]]],
	    name = name_list[0]
		)

		trace2 = go.Bar(
	    x=['last.fm Playcount (in thousands)'],
	    y=[play_dict[name_list[1]]],
	    name = name_list[1]
		)

		trace3 = go.Bar(
	    x=['last.fm Playcount (in thousands)'],
	    y=[play_dict[name_list[2]]],
	    name = name_list[2]
		)

		trace4 = go.Bar(
	    x=['last.fm Playcount (in thousands)'],
	    y=[play_dict[name_list[3]]],
	    name = name_list[3]
		)

		trace5 = go.Bar(
	    x=['last.fm Playcount (in thousands)'],
	    y=[play_dict[name_list[4]]],
	    name = name_list[4]
		)

		data = [trace1, trace2, trace3, trace4, trace5]
		layout = go.Layout(
			barmode='group',
	    	autosize=False,
	    	width=700,
	    	height=700,
	    	margin=go.layout.Margin(
	        l=50,
	        r=50,
	        b=150,
	        t=100,
	        pad=4),
	    )

		fig = go.Figure(data=data, layout=layout)
		py.plot(fig, filename='grouped-bar')

def graph_year_popularity(date_dict, year1, year2):

	year1_string = "Year: " + str(year1)
	year2_string = "Year: " + str(year2)
	trace1 = go.Bar(
            x=[year1_string, year2_string],
            y=[date_dict[year1], date_dict[year2]]
        )

	data = [trace1]

	layout = go.Layout(
    	autosize=False,
    	width=700,
    	height=700,
    	margin=go.layout.Margin(
        l=50,
        r=50,
        b=150,
        t=100,
        pad=4),
    )

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='popularity')

def graph_tags(tag_dict):

	#From https://stackoverflow.com/questions/613183/how-do-i-sort-a-dictionary-by-value
	sorted_tag_dict = sorted(tag_dict.items(), key=lambda kv: kv[1], reverse=True)

	trace1 = go.Bar(
            x=[sorted_tag_dict[0][0], sorted_tag_dict[1][0], sorted_tag_dict[2][0], sorted_tag_dict[3][0], sorted_tag_dict[4][0]],
            y=[sorted_tag_dict[0][1], sorted_tag_dict[1][1], sorted_tag_dict[2][1], sorted_tag_dict[3][1], sorted_tag_dict[4][1]]
        )

	data = [trace1]

	layout = go.Layout(
    	autosize=False,
    	width=700,
    	height=700,
    	margin=go.layout.Margin(
        l=50,
        r=50,
        b=150,
        t=100,
        pad=4),
    )

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='tags')

def graph_related_artists(artist_pop_dict, artist_follower_dict, artist, name_list, metric):
	
	'''trace1 = go.Bar(
            x=[artist.name, name_list[0], name_list[1], name_list[2], name_list[3]],
            y=[artist.popularity, artist_dict[name_list[0]], artist_dict[name_list[1]], artist_dict[name_list[2]], artist_dict[name_list[3]]]
		)

	data = [trace1]

	layout = go.Layout(
    	autosize=False,
    	width=700,
    	height=700,
    	margin=go.layout.Margin(
        l=50,
        r=50,
        b=150,
        t=100,
        pad=4),
    )

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='related-artists')'''

	'''trace1 = go.Bar(
    x=['Spotify Popularity', 'Twitter Followers (in thousands)'],
    y=[artist.popularity, artist.followers / 1000],
    name = artist.name
	)

	trace2 = go.Bar(
    x=['Spotify Popularity', 'Twitter Followers (in thousands)'],
    y=[artist_pop_dict[name_list[0]], artist_follower_dict[name_list[0]]],
    name = name_list[0]
	)

	trace3 = go.Bar(
    x=['Spotify Popularity', 'Twitter Followers (in thousands)'],
    y=[artist_pop_dict[name_list[1]], artist_follower_dict[name_list[1]]],
    name = name_list[1]
	)

	trace4 = go.Bar(
    x=['Spotify Popularity', 'Twitter Followers (in thousands)'],
    y=[artist_pop_dict[name_list[2]], artist_follower_dict[name_list[2]]],
    name = name_list[2]
	)

	trace5 = go.Bar(
    x=['Spotify Popularity', 'Twitter Followers (in thousands)'],
    y=[artist_pop_dict[name_list[3]], artist_follower_dict[name_list[3]]],
    name = name_list[3]
	)


	data = [trace1, trace2, trace3, trace4, trace5]
	layout = go.Layout(
		barmode='group',
    	autosize=False,
    	width=700,
    	height=700,
    	margin=go.layout.Margin(
        l=50,
        r=50,
        b=150,
        t=100,
        pad=4),
    )

	fig = go.Figure(data=data, layout=layout)
	py.plot(fig, filename='grouped-bar')'''

	if metric == "spotify":
		trace1 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[artist.popularity],
	    name = artist.name
		)

		trace2 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[artist_pop_dict[name_list[0]]],
	    name = name_list[0]
		)

		trace3 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[artist_pop_dict[name_list[1]]],
	    name = name_list[1]
		)

		trace4 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[artist_pop_dict[name_list[2]]],
	    name = name_list[2]
		)

		trace5 = go.Bar(
	    x=['Spotify Popularity'],
	    y=[artist_pop_dict[name_list[3]]],
	    name = name_list[3]
		)


		data = [trace1, trace2, trace3, trace4, trace5]
		layout = go.Layout(
			barmode='group',
	    	autosize=False,
	    	width=700,
	    	height=700,
	    	margin=go.layout.Margin(
	        l=50,
	        r=50,
	        b=150,
	        t=100,
	        pad=4),
	    )

		fig = go.Figure(data=data, layout=layout)
		py.plot(fig, filename='grouped-bar')

	elif metric == "twitter":
		
		trace1 = go.Bar(
	    x=['Twitter Followers (in thousands)'],
	    y=[artist.followers / 1000],
	    name = artist.name
		)

		trace2 = go.Bar(
	    x=['Twitter Followers (in thousands)'],
	    y=[artist_follower_dict[name_list[0]]],
	    name = name_list[0]
		)

		trace3 = go.Bar(
	    x=['Twitter Followers (in thousands)'],
	    y=[artist_follower_dict[name_list[1]]],
	    name = name_list[1]
		)

		trace4 = go.Bar(
	    x=['Twitter Followers (in thousands)'],
	    y=[artist_follower_dict[name_list[2]]],
	    name = name_list[2]
		)

		trace5 = go.Bar(
	    x=['Twitter Followers (in thousands)'],
	    y=[artist_follower_dict[name_list[3]]],
	    name = name_list[3]
		)


		data = [trace1, trace2, trace3, trace4, trace5]
		layout = go.Layout(
			barmode='group',
	    	autosize=False,
	    	width=700,
	    	height=700,
	    	margin=go.layout.Margin(
	        l=50,
	        r=50,
	        b=150,
	        t=100,
	        pad=4),
	    )

		fig = go.Figure(data=data, layout=layout)
		py.plot(fig, filename='grouped-bar')

def process_command(command):
	command_split = command.split()
	first = command_split[0]
	metric = "spotify"
	#tags artistname=?
	if first == "tags":
		command = command_split[1:]
		new_command = ' '.join(command)
		name = new_command.split('=')[1]
		query_tags(name)
	#compare 
		#related artistname=?
	if first == "related":
		command = command_split[1:]
		new_command = ' '.join(command)
		command_split = new_command.split()
		for word in command_split:
			if "artist" in word:
				name = word.split('=')[1]
			if "metric" in word:
				metric = word.split('=')[1]
		query_related_artists(name,metric)
		#TODO: artistname1=? artistname2=? - don't have a function for this yet
	#years artistname=? year1=? year2=?
	#fix divide by zero error lol
	if first == "years":
		command = command_split[1:]
		new_command = ' '.join(command)
		command_split = new_command.split()
		for word in command_split:
			if "artist" in word:
				name = word.split('=')[1]
			if "year1" in word:
				year1 = word.split('=')[1]
			if "year2" in word:
				year2 = word.split('=')[1]
		query_release_dates(name,year1,year2)
	#songs artistname=?
	#If I separate them do I still need to do it in thousands???
	if first == "songs":
		command = command_split[1:]
		new_command = ' '.join(command)
		command_split = new_command.split()
		for word in command_split:
			if "artist" in word:
				name = word.split('=')[1]
			if "metric" in word:
				metric = word.split('=')[1]
		query_top_songs(name,metric)

def get_top_artists():
	base_url = 'http://ws.audioscrobbler.com/2.0/'
	params = {}
	params['limit'] = 2
	params['method'] = "chart.getTopArtists"
	params['format'] = "json"
	params['api_key'] = last_fm_token
	result = make_request_using_cache_last_fm(base_url,params)	

	for artist in result['artists']['artist']:
		search_for_artist(artist['name'])

def interactive_prompt():
	response = ''
	while response != 'exit':
		response = input('Enter a command: ')
		if response != 'exit':
			#try:
			process_command(response)
			#except:
				#print("Unable to process command.")
				#continue

create_artists()
create_songs()

get_top_artists()

#if __name__=="__main__":
    #interactive_prompt()
