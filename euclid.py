from itertools import cycle

# Where n is the number of steps in the rhythm and k is the number
# of "ones" in the rhythm
def euclidean_rhythm(k,n):
    # If either parameter is zero, return 
    # a generator that always returns zero
    if k == 0 or n == 0: return cycle([0])

    zeros, ones = [n-k], [k]
    def euclid(m,k,steps):
        if k == 0 or zeros[0] == 0: 
            return map(lambda x: x +[0]*(zeros[0]/ones[0]), steps)
        else:      
            zeros[0] = zeros[0]-k
            return euclid(k, m % k, map(lambda x: x+[0], 
                          steps[:k]) + steps[k:])

    return cycle(reduce(lambda x,y: x+y, 
                        euclid(max(k,m), min(k,m), 
                        [[1]]*k)))

