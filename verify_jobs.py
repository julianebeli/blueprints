# courses have to be in same subaccount to be associated

import __init__
import re
from db_reader import db_reader
import json
from dataclasses import dataclass
from typing import List
import logging
from pluck import pluck
from collections import namedtuple

from tests import blueprint_id, association_ids,  get_hash, get_dates, get_subaccounts
from tests import get_course, get_associated_course_information, create_blueprint, create_associations, get_course_id


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logfile = logging.FileHandler('the.log')
logfile.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(message)s')
logfile.setFormatter(formatter)
logger.addHandler(logfile)
# logger.basicConfig(filename='the.log', format=, level=logging.INFO)
logger.info('Started')


@dataclass
class Entry:
    checksum: str
    date: str
    duration: str
    email: str
    name: str
    school: str
    blueprint: List[int]
    associations: List[int]
    success: bool = False
    error: str = ''


def pp(t):
    print(json.dumps(t, indent=4))


def record(entry):
    print(f'recording {entry}')
    logger.info(f'{entry}')
    pass


# https://canvas.education.tas.gov.au/courses/56778
data = db_reader('data.db', 'requests')
rows = [data.nt(*x) for x in data.connection.cursor.execute(data.sql_select)]
# rows = [x for x in rows if not x.Completed]


entries: List[Entry] = []


for row in rows[-2:]:
    checksum = get_hash(row)
    dates = get_dates(row)
    date = dates['start']
    duration = dates['duration']

    blueprint = blueprint_id(row)
    associations = association_ids(row)
    print(f"associations: {associations}")
    e = Entry(checksum, str(date), str(duration), row.Email,
              row.Name, row.School, blueprint, associations)

    if not blueprint:
        # no blueprint course in request
        e.error = 'no blueprint course in request'
        entries.append(e)
        record(e)
        continue

    blueprint_course_data = list(map(get_course, blueprint))[0]
    print('bcd')
    print(blueprint_course_data)

    if 'errors' in blueprint_course_data[0].keys():
        # course doesn't exist in Canvas
        e.error = blueprint_course_data[0]['errors'][0]['message'] + ' - blueprint'
        entries.append(e)
        record(e)
        continue

    if blueprint_course_data[0]['total_students'] != 0:
        # blueprint course has students
        e.error = f"blueprint can not have students [{blueprint_course_data[0]['total_students']}]"
        entries.append(e)
        record(e)
        continue
    print(f"is course a blueprint? {blueprint_course_data[0]['blueprint']}")
    if not blueprint_course_data[0]['blueprint']:
        # create blueprint course
        blueprint_course_data = create_blueprint(blueprint)
        # print(f"creating blueprint")

    else:
        # course is a blueprint so you can ask who's associated
        already_associated = get_associated_course_information(blueprint)
        print('already associated')
        print(already_associated)
        associations_required = set(associations) - set(already_associated)
        if not associations_required:
            e.success = True
            e.error = 'all courses already associated'
            entries.append(e)
            record(e)
            continue
    print('associations required')
    print(associations_required)
    course_data = list(map(get_course, associations_required))
    print("association course data:")
    print(course_data)
    course_data = course_data[0]
    subaccounts = get_subaccounts(blueprint_course_data[0]['account_id'])
    associables = []

    for course in course_data:
        # print(course)

        if 'errors' in course.keys():
            # course doesn't exist in Canvas
            e.error = f"{course['errors'][0]['message']} - association [{course}]"
            entries.append(e)
            record(e)
            continue
        course_account = set([course['account_id']])
        if not (course_account <= subaccounts):
            # course not in right subaccount
            e.error = 'Incorrect sub_account'
            entries.append(e)
            record(e)
            continue

        associables.append(course['id'])

    if not associables:
        # nothing to associate
        e.error = 'no course to associate to blueprint'
        entries.append(e)
        record(e)
        continue

    # finally do associations
    create_associations(blueprint[0], associables)
    e.associations = associables
    e.success = True
    record(e)


for entry in entries:
    print(entry)


def courses(attr):
    def extract(u):
        if u:
            return u[0]

    return list(map(lambda y: y[0].split('/')[-1], filter(
        extract, [get_course_id(getattr(x, attr)) for x in rows])))


associations = set(courses('Coursestoassociate'))
print(associations)
blueprint_courses = set(courses('CourseID') +
                        (courses('UseexistingBlueprintcourse')))
print(blueprint_courses)

print(len(associations), len(blueprint_courses))

all_courses = blueprint_courses | associations
print(all_courses, len(all_courses))
print(blueprint_courses & associations)

# Now we need to anaylse each row and do these tests
# Basic tests:
#     Is there a blueprint course in the request?


# If the requests is for associations is the blueprint
#     1. a existing course
#     2. a blueprint course
#     3. has no students
#     4. the courses are all in the same subaccount.
#     5. the association courses exist.
