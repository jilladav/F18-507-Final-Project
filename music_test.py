from music import *
import unittest

class testArtistCreation(unittest.TestCase):
	
	def testConstructor(self):
		a1 = Artist()

		self.assertEqual(a1.id, 0)
		self.assertEqual(a1.name, "None")
		self.assertEqual(a1.genre, "None")
		self.assertEqual(a1.top_songs, [])
		self.assertEqual(a1.followers, 0)
		self.assertEqual(a1.popularity, 0)

class testSongCreation(unittest.TestCase):
	
	def testConstructor(self):
		s1 = Song()

		self.assertEqual(s1.id, 0)
		self.assertEqual(s1.name, "None")
		self.assertEqual(s1.artist, "None")
		self.assertEqual(s1.popularity, 0)
		self.assertEqual(s1.release, "None")
		self.assertEqual(s1.tags, [])
		self.assertEqual(s1.listeners, 0)
		self.assertEqual(s1.playcount, 0)

class testDatabase(unittest.TestCase):
	def testArtistTable(self):
		conn = sqlite3.connect(DBNAME)
		cur = conn.cursor()

		statement = '''SELECT Name FROM Artists'''
		results = cur.execute(statement)
		result_list = results.fetchall()
		self.assertIn(('Katy Perry',), result_list)
		self.assertEqual(len(result_list), 100)

		statement = '''SELECT Name FROM Artists ORDER BY TwitterFollowers DESC'''
		results = cur.execute(statement)
		result_list = results.fetchall()
		self.assertEqual(('Katy Perry',), result_list[0])

		conn.close()

	def testSongTable(self):
		conn = sqlite3.connect(DBNAME)
		cur = conn.cursor()

		statement = '''SELECT Name FROM Songs'''
		results = cur.execute(statement)
		result_list = results.fetchall()
		self.assertIn(('Crazy In Love',), result_list)
		self.assertGreater(len(result_list), 3000)

		conn.close()

class testQueries(unittest.TestCase):
	
	def testTopSongsQueries(self):
		top = query_top_songs("Adele")
		self.assertIn("Hello", top)
		top = query_top_songs("Ellie Goulding")
		self.assertIn("Burn", top)

	def testTagQueries(self):
		tags = query_tags("Adele")
		self.assertIn("pop", tags.keys())
		tags = query_tags("Britney Spears")
		self.assertIn("dance", tags.keys())

	def testReleaseYearQueries(self):
		years = query_release_dates("Adele", 2016, 2011)
		self.assertIn(2016, years.keys())
		self.assertIn(2011, years.keys())
		self.assertGreater(years[2016], 0)
		self.assertGreater(years[2011], 0)

	def testRelatedArtistQueries(self):
		related = query_related_artists("Katy Perry")
		self.assertIn("Miley Cyrus", related)

	def testComparisonQueries(self):
		compare = query_comparisons("Katy Perry", "Miley Cyrus")
		compare1 = compare[0]
		compare2 = compare[1]
		self.assertGreater(compare1["followers"], 1000000)
		self.assertGreater(compare2["followers"], 1000000)
		self.assertGreater(compare1["popularity"], 0)
		self.assertGreater(compare2["popularity"], 0)

unittest.main()