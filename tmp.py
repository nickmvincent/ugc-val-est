from urllib.parse import unquote

x = '%27'
y = unquote(x)
print(y)