

class Foo:
    
    def split(self, words, results, prefix):

        for i in range(1, len(words)):
            first = words[:i]
            second = words[i:]
            
            if len(prefix) > 0: 
                results.append("{}, {}, {}".format(prefix, self.concat(first), self.concat(second)))
                new_prefix = prefix + ", " + self.concat(first)
            else: 
                results.append("{}, {}".format(self.concat(first), self.concat(second)))
                new_prefix = self.concat(first)
            
            second_split = self.split(second, results, new_prefix)

        
        
    def concat(self, words):
        return "".join(words)
        
if __name__ == '__main__':

    results = []
    foo = Foo()
    foo.split("a b c d e f".split(), results, "")
    
    print("\n".join(results))
