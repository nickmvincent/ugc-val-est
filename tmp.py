import json
from json.decoder import JSONDecodeError


filepath = 'C:\\Users\\Nick\\Downloads'
filename = 'stackoverflow-questions2%2F000000000046'

full = '\\'.join([filepath, filename])

with open(full, 'r', encoding='utf8') as jsonfile:
    for line in jsonfile:
        try:
            data = json.loads(line)
        except JSONDecodeError:
            print('JSON err')
            data = line
        print(line)