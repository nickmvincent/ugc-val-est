
from itertools import zip_longest
def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


x = ['1', '2', '3', '4', '5', '6', '7']

for group in grouper(x, 3):
    group = [member for member in group if member]
    print(group)