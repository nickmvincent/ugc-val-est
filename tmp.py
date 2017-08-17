
from itertools import zip_longest
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    ret = zip_longest(*args, fillvalue=fillvalue)
    return [member for member in ret if member is not None]


x = ['1', '2', '3', '4', '5', '6', '7']

for group in grouper(x, 3):
    print(group)