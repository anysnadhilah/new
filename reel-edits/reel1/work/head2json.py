import json, re, statistics, sys
out = {}
for l in open(sys.argv[1]):
    m = re.match(r'(\S+)\s+[\d.]+s\s+(.*)', l)
    if not m: continue
    tops = [int(x) for x in re.findall(r'head top\s+(\d+)', m.group(2))]
    if tops: out[m.group(1)] = min(tops)   # highest point the head reaches in the segment
json.dump(out, open('work/head.json', 'w'), indent=1)
print(out)
