## Data Sources:

Spotify API - https://developer.spotify.com/documentation/web-api/

last.fm API - https://www.last.fm/api

Twitter API - https://developer.twitter.com/en/docs.html

#### secret_data.py

In order to run the program, you need to have a file called secret_data.py that includes the following:

Consumer key, consumer access, access key, and access secret for the Twitter API.

Client ID and client secret for the Spotify API.

Token and secret for the last.fm API.

The user also needs to create an account on plotly.com.

## Description
All of the code is contained in one main file, music.py, and then one unittest file, music_test.py.

#### music.py
music.py processes user commands and updates the database as necessary in order to display visual information about an artist.

#### Processing functions:
search_for_artist(): takes a name of an artist as input and creates an instance of the Artist class, which searches the Spotify API, last.fm API, and Twitter API for all of the necessary information and then updates the database

query_top_songs(): gets the top 5 Spotify songs for an artist from the database

query_release_dates(): gets the average popularity, playcount, and listeners for songs by an artist from the specified years

query_tags: gets the top 5 tags from last.fm based on an artist's songs

query_related_artists(): gets the related artists for an artist from the database

#### Classes:
Artist:

Contains an artist's name, genre, top 5 songs, Twitter followers, and Spotify popularity

class methods:

process_json_dict(): processes a json dictionary to update information about the artist

get_top_tracks(): gets the top tracks for an artist from Spotify and updates top tracks list

get_twitter_data(): gets Twitter data about the aritst and updates followers

get_last_fm_songs(): gets more songs by the artist from last.fm

str(): returns the artist's name

Song:

Contains a song's name, artist, Spotify popularity, release date, top 5 tags from last.fm, last.fm listeners, and last.fm playcount

process_json_dict(): processes a json dictionary to update information about the song

get_last_fm_data(): gets last.fm data about the song and updates it

str(): returns the song's name

#### User Guide
There are four main user inputs.

For each, any parameters that need to be specified (e.g. a specific artist or metric) must be separated by commas.

#### tags

Graphs the most popular tags for an artist.

example input:

tags artist=Adele




#### compare

Compare an artist to related artists or specify an artist to compare them to, and by what metric.

Metric options:

spotify - Spotify popularity (default)

twitter - Twitter followers

example input:

compare related artist=Adele

compare artist1=Adele,artist2=Katy Perry,metric=twitter




#### years

Compare the popularity of an artist's songs from certain years and specify by what metric.

Metric options:

spotify - average Spotify popularity (default)

listeners - average number of last.fm listeners

playcount - average last.fm playcount

example input:

years artist=Adele,year1=2016,year2=2011,metric=listeners




#### songs

Compare the popularity of an artist's current top Spotify songs and specify by what metric.

Metric options:

spotify - Spotify popularity (default)

listeners - number of last.fm listeners

playcount - last.fm playcount

example input:

songs artist=Adele,metric=playcount

#### remake tables
A user can also remake tables and repopulate the database with:

remake tables

