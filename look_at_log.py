from dataclasses import dataclass
from typing import List
import re


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

print(lines)
