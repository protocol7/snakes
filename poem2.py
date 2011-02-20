

class Foo:
    
    def sort(self, tokens):
        return sorted(tokens, key=lambda s: len(s))

    def split(self, words):
        results = [self.concat(words)]
        
        self.split_internal(words, results, "")
        
        return self.sort(results)
    
    def split_internal(self, words, results, prefix):

        for i in range(1, len(words)):
            first = words[:i]
            second = words[i:]
            
            if len(prefix) > 0: 
                results.append("{}, {}, {}".format(prefix, self.concat(first), self.concat(second)))
                new_prefix = prefix + ", " + self.concat(first)
            else: 
                results.append("{}, {}".format(self.concat(first), self.concat(second)))
                new_prefix = self.concat(first)
            
            second_split = self.split_internal(second, results, new_prefix)

        
        
    def concat(self, words):
        return "".join(words)
        
if __name__ == '__main__':


    foo = Foo()
    results = foo.split("a b c d".split())
    
    print("\n".join(results))

