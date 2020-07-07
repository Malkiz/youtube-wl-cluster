import numpy as np
import pandas as pd
import gower

# all numbers
# all strings
# mixed

# same, 25%, 50%, 75%, 0%

s1 = '1'
s2 = '1000'
n1 = 1
n2 = 1000
types = {
    'numbers': [n1, n2, 2, 2000],
    'strings': [s1, s2, '2', '2000'],
    'mixed'  : [n1, n2, s1, s2]
}
orders = {
    'same': lambda a: [a,a],
    '25%': lambda a: [a, [a[0],a[1],a[2],a[2]]],
    '25% 2': lambda a: [a, [a[0], a[0], a[2], a[3]]],
    '50%': lambda a: [a, [a[0], a[1], a[0], a[1]]],
    '50% 2': lambda a: [a, [a[0], a[2], a[1], a[3]]],
    '50% 3': lambda a: [a, [a[3], a[1], a[2], a[0]]],
    '75%': lambda a: [a, [a[0], a[0], a[0], a[0]]],
    '75% 2': lambda a: [a, [a[1], a[0], a[3], a[3]]],
    '100%': lambda a: [a, [a[3], a[2], a[1], a[0]]]
}

for k, a in types.items():
    print(k)
    for o, func in orders.items():
        print(o)
        b = func(a)
        X = pd.DataFrame(b)
        X['c'] = 'c'
        print(X)
        print (gower.gower_matrix(X))

