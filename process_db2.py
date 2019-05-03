import __init__
import hashlib
import json
from db_reader import db_reader
from api.requestor import API
from datetime import datetime
import re
from tests import get_course_id, get_hash, get_course
from subaccount_info_reader import get_parent, get_child

course_id_stem = re.compile(r"/courses/(\d+)")
course_id_number = re.compile(r"^(\d+)$")

now = str(datetime.now())
print(now)

cache_time = 60*60*24
api = API(server='prod', cache=None)
data = db_reader('data.db', 'requests')
# print(data)

rows = [data.nt(*x) for x in data.connection.cursor.execute(data.sql_select)]
# rows = [x for x in rows if not x.Completed]
# print(len(rows))


jobs = []
for row in rows:
    blueprint = list(set((filter(lambda x: x, (get_course_id(row.CourseID) +
                                               get_course_id(row.UseexistingBlueprintcourse))))))
    associations = list(
        set(filter(lambda x: x, get_course_id(row.Coursestoassociate))))
    jobs.append(dict(checksum=get_hash(row),
                     blueprint=blueprint, associations=associations))


def qualities(course_id):

    course_data = get_course(course_id)

    data = dict(course_id=course_id, error='')
    if not course_data.response_error:
        data['course_subaccount'] = course_data.results[0]['account_id']
        data['is_blueprint'] = course_data.results[0]['blueprint']
        data['student_count'] = course_data.results[0]['total_students']
    else:
        message = course_data.results[0]['errors'][0]['message']
        if message == 'The specified resource does not exist.':
            data['error'] = f"course {course_id} does not exist"
        else:
            data['error'] = message

    return data


def course_data(j):

    if not j['blueprint']:
        blueprint_error = 'no blueprint course specified'
        return dict(checksum=j['checksum'], error=blueprint_error)
    else:
        blueprint_course_id = j['blueprint'][0]

    blueprint_qualities = qualities(blueprint_course_id)
    association_data = list(map(qualities, j['associations']))
    return dict(checksum=j['checksum'], blueprint=blueprint_qualities, associations=association_data)


job_list = list(map(course_data, jobs))
for job in job_list:
    print(job)

    # checks to do:
    # parent = get_parent(course_data.results[0]['account_id'])
    # if parent:
    #     error = f"move to parent subaccount {parent}"
    # child = get_child(course_data.results[0]['account_id'])
    # if is_blueprint:
    #     error = "course is already a blueprint"
    # if student_count != 0:
    #     error = "blueprint has students"

exit()
