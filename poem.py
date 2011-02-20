import re

class Sentence:
    
    def __init__(self, sentence):
        self.sentence = sentence
        self.words = sentence.split()
    
    def __sort(self, tokens):
        return sorted(tokens, key=lambda s: len(s))

    def as_tokens(self):
        results = [self.__concat(self.words)]
        
        self.__split(self.words, results, "")
        
        return self.__sort(results)
    
    def __split(self, words, results, prefix):

        for i in range(1, len(words)):
            first = words[:i]
            second = words[i:]
            
            if len(prefix) > 0: 
                results.append("{}, {}, {}".format(prefix, self.__concat(first), self.__concat(second)))
                new_prefix = prefix + ", " + self.__concat(first)
            else: 
                results.append("{}, {}".format(self.__concat(first), self.__concat(second)))
                new_prefix = self.__concat(first)
            
            second_split = self.__split(second, results, new_prefix)

        
        
    def __concat(self, words):
        return " ".join(words)
        
class Poem:
    
    def __init__(self, poem):
        self.poem = poem
        
    def as_tokens(self):
        pattern = re.compile("[^\w\t ]+")
        
        tokens = pattern.split(self.poem)
        
        for i in range(0, len(tokens)):
            tokens[i] = tokens[i].strip()
        
        return tokens
        
    def as_sentences(self):
        tokens = self.as_tokens()

        sentences = []
        for token in tokens:
            sentences.append(Sentence(token))

        return sentences
        
if __name__ == '__main__':
    sentence = Sentence("a b c d")
    results = foo.as_tokens()
    
    print("\n".join(results))

