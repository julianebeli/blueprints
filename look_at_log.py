from dataclasses import dataclass
from typing import List
import re
import json


@dataclass
class Entry:
    checksum: str
    date: str
    duration: str
    email: str
    blueprint: List[int]
    associations: List[int]
    success: bool = False
    name: str = ''
    school: str = ''
    error: str = ''


lines = []

with open('the.log', 'r') as f:
    for line in f.readlines():
        found = re.findall(r'Entry\(.*\)', line)
        if found:
            lines.append(eval(found[0]))
        # lines.append(line.strip())


jobs: dict = {}
for entry in lines:
    jobs[entry.checksum] = set()
for entry in lines:
    if entry.error:
        jobs[entry.checksum].add(entry.error)

print(jobs)
# print(json.dumps(jobs, indent=4))
