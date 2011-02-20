import poem
import unittest
import io

class TestSentence(unittest.TestCase):
    
    def test_as_tokens(self):
        sentence = poem.Sentence("a b c d")
        actual = sentence.as_tokens()
        
        expected = [
            "a b c d",
            "a,b c d",
            "a b,c d",
            "a b c,d",
            "a,b,c d",
            "a,b c,d",
            "a b,c,d",
            "a,b,c,d"
        ]

        self.assertEqual(expected, actual)
        
    def test_as_tokens_single_word(self):
        sentence = poem.Sentence("a")
        actual = sentence.as_tokens()

        expected = [
            "a"
        ]

        self.assertEqual(expected, actual)

class TestPoem(unittest.TestCase):

    def test_as_tokens(self):
        the_poem = poem.Poem("a, b c. d.\n e f")
        actual = the_poem.as_tokens()

        expected = ["a", "b c", "d", "e f"]

        self.assertEqual(expected, actual)

    def test_as_sentences(self):
        the_poem = poem.Poem("a, b c. d.\n e f")
        actual = the_poem.as_sentences()

        self.assertEqual(4, len(actual))
        self.assertTrue(isinstance(actual[0], poem.Sentence))

class TestSearchResult(unittest.TestCase):

    def test_coverage(self):
        results = [
            ("a b", "href"),
            ("c", None),
            ("d e", "href"),
            ("f", None),
        ]
        
        sentence = "a b c d e f"
        
        search_result = poem.SearchResult(sentence, results)

        self.assertEqual(4/6, search_result.coverage())

class FakeSpotify:
    
    def search_all(self, track_names):
        return [
            ("track1", "spotify:track:6JEK0CvvjDjjMUBFoXShNZ"),
            ("track2", None)
        ]
    

class TestPoemSearch(unittest.TestCase):

    def test_search_and_print(self):
        search = poem.PoemSearch(FakeSpotify())
        
        out = io.StringIO()
        search.search_and_print("STRANGER! if you, passing", out)

        out.seek(0)
        
        self.assertEqual("track1: spotify:track:6JEK0CvvjDjjMUBFoXShNZ\n", out.readline())
        self.assertEqual("track2\n", out.readline())


class FakeHttpClient:

    def request(self, url, method):
        # Return some simplfied JSON
        return ({}, """{"tracks" : [
            { "name" : "track1", "href" : "href1" },
            { "name" : "track2", "href" : "href2"  }
        ]}""".encode("utf-8"))

class TestSpotify(unittest.TestCase):

    def test_search(self):
        spotify = poem.Spotify(FakeHttpClient())

        actual = spotify.search("Track2")

        self.assertEqual("href2", actual)

    def test_search_all(self):
        spotify = poem.Spotify(FakeHttpClient())

        actual = spotify.search_all(["track1", "Track2", "dummy"])

        expected = [
            ("track1", "href1"),
            ("Track2", "href2"),
            ("dummy", None),
        ]

        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()