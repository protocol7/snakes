import re
import httplib
import optparse
import json
import sys

class Sentence:
    """ Represents a sentence within a poem. Sentences are delimited by punctation characters and themselves
        only contains alphanumeric words and whitespaces
        """
    
    def __init__(self, sentence):
        self.sentence = sentence
        self.words = sentence.split()
    
    def __sort(self, tokens):
        return sorted(tokens, key=lambda s: s.count(","))

    def as_tokens(self):
        """ Returns all permutations of how the sentence can be split into unique combinations of words """
        
        results = [self.__concat(self.words)]
        
        self.__split(self.words, results, "")
        
        return self.__sort(results)
    
    def __split(self, words, results, prefix):

        for i in range(1, len(words)):
            first = words[:i]
            second = words[i:]
            
            if len(prefix) > 0: 
                results.append("{},{},{}".format(prefix, self.__concat(first), self.__concat(second)))
                new_prefix = prefix + "," + self.__concat(first)
            else: 
                results.append("{},{}".format(self.__concat(first), self.__concat(second)))
                new_prefix = self.__concat(first)
            
            second_split = self.__split(second, results, new_prefix)

        
        
    def __concat(self, words):
        return " ".join(words)
        
class Poem:
    """ Representens a complete poem """
    
    def __init__(self, poem):
        self.poem = poem
        
    def as_tokens(self):
        """ Returns the sentences of a poem, as strings """
        pattern = re.compile("[^\w\t ]+")
        
        tokens = pattern.split(self.poem)
        
        for i in range(0, len(tokens)):
            tokens[i] = tokens[i].strip()
        
        return tokens
        
    def as_sentences(self):
        """ Returns the sentences of a poem and Sentence types """
        
        tokens = self.as_tokens()

        sentences = []
        for token in tokens:
            sentences.append(Sentence(token))

        return sentences
        
        
class Spotify():
    
    def __init__(self, http_client = httplib.Http(timeout=20)):
        self.http_client = http_client
    
    def search(self, track_name):  
        """ Searches for a track with a specific name, returns the Spotify link for the first track found"""
         
        # Limited to doing one attempt, since more attempt seldome returns better results
        (headers, content) = self.http_client.request("http://ws.spotify.com/search/1/track.json?q={}".format(track_name), method="GET")

        # UTF-8 is specified for the service
        tracks = json.loads(content.decode("utf-8"))
        
        for track in tracks.get("tracks"):
            if track_name.lower() == track.get("name").lower():
                return track.get("href")

    def search_all(self, track_names):
        """ Searches for tracks with the specified track names. Returns a list of tuples of the track name and track link
            (if any match is found, None otherwise)
          """
        
        results = []
        for track_name in track_names:
            results.append((track_name, self.search(track_name)))

        return results

class SearchResult:
    """ Represents a sentence and it's tokens and their matching Spotify tracks """
    
    def __init__(self, sentence, results):
        self.sentence = sentence
        self.results = results
        
    def coverage(self):
        """ Returns the percentage (0.0-1.0) of words in the sentence that this search result covers. """
        
        total_no_words = len(self.sentence.split())
        words_with_href = 0
        
        # count the number of words that has a matching href
        for result in self.results:
            words, href = result
            
            if not href == None:
                words_with_href = words_with_href + len(words.split())
    
        return words_with_href/total_no_words
        
    def format(self):
        """ Formats a search result for human consumation """
        
        rows = []
        for result in self.results:
            words, href = result
            
            if not href == None:
                rows.append(words + ": " + href)
            else:
                # no match found, just print words
                rows.append(words)
        
        return "\n".join(rows)

class PoemSearch:
    """ The main acting class. Performs a search on Spotify for matching track for a provided poem """
    
    
    def __init__(self, spotify_client):
        self.spotify_client = spotify_client

    def search_and_print(self, poem_str, out):
        """ Searches for Spotify tracks matching the poem. Will attempt to 
            maximize the number of words that gets matched by a track.
            
            Takes a stream to write to in order to provide quick feedback for users.
        """
        poem = Poem(poem_str)

        for sentence in poem.as_sentences():
            best_result = None
            for tokens in sentence.as_tokens():
                # find one combination of tokens where most of the words match

                tokens = tokens.split(",")

                search_result = SearchResult(sentence.sentence, self.spotify_client.search_all(tokens))

                if search_result.coverage() == 1.0:
                    best_result = search_result 
                    break
                elif best_result == None or search_result.coverage() > best_result.coverage():
                    best_result = search_result

            out.write(best_result.format())
            out.write("\n")
        
        

if __name__ == '__main__':
    parser = optparse.OptionParser("usage: %prog poem")
    
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("You must specify a poem")
    
    poem = args[0]

    try:
        search = PoemSearch(Spotify())
        
        search.search_and_print(poem, sys.stdout)
    except KeyboardInterrupt:
        pass
