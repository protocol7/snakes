import poem2
import unittest

class TestSentence(unittest.TestCase):
    
    def test_as_tokens(self):
        sentence = poem2.Sentence("a b c d")
        actual = sentence.as_tokens()
        
        expected = [
            "a b c d",
            "a, b c d",
            "a b, c d",
            "a b c, d",
            "a, b, c d",
            "a, b c, d",
            "a b, c, d",
            "a, b, c, d"
        ]

        self.assertEqual(expected, actual)
        
    def test_as_tokens_single_word(self):
        sentence = poem2.Sentence("a")
        actual = sentence.as_tokens()

        expected = [
            "a"
        ]

        self.assertEqual(expected, actual)

class TestPoem(unittest.TestCase):

    def test_as_tokens(self):
        poem = poem2.Poem("a, b c. d.\n e f")
        actual = poem.as_tokens()

        expected = ["a", "b c", "d", "e f"]

        self.assertEqual(expected, actual)

    def test_as_sentences(self):
        poem = poem2.Poem("a, b c. d.\n e f")
        actual = poem.as_sentences()

        self.assertEqual(4, len(actual))
        self.assertTrue(isinstance(actual[0], poem2.Sentence))


if __name__ == '__main__':
    unittest.main()