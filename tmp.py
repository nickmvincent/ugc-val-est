valstr = "40.131     14.114      2.843      0.004     12.468     67.794"
padded_vals = valstr.split(' ')
vals = [val.strip() for val in padded_vals if val]
print(','.join(vals))

