import __init__
from __init__ import here
import hashlib
import json
from pathlib import Path
# from db_reader import db_reader
from api.requestor2 import API
from datetime import datetime
import re
from tests import get_course_id, get_hash, get_course, create_blueprint2, create_associations2, valid_associations, correct_subaccount
from subaccount_info_reader import get_parent, get_child
from source_data import get_data, write_data


cache_time = 60 * 60 * 24
api = API(server='beta', cache=None)
# data = db_reader('data.db', 'requests')
# print(data)

# rows = [data.nt(*x) for x in data.connection.cursor.execute(data.sql_select)][:10]
# rows = [x for x in rows if not x.Completed]

datafile = Path(here) / 'raw_data' / 'Blueprint Course Management 1 (14).xlsx'
rows = get_data(datafile)
# print(rows)

courses = []
for row in rows:
    who = dict(date=row.Starttime, name=row.Name, email=row.Email, school=row.School, create_blueprint=row.CourseID, use_blueprint=row.UseexistingBlueprintcourse, associations=row.Coursestoassociate)
    blueprint = list(set(filter(lambda x: x, (get_course_id(row.CourseID) +
                                              get_course_id(row.UseexistingBlueprintcourse)))))
    associations = list(set(filter(lambda x: x, get_course_id(row.Coursestoassociate))))
    courses.append(dict(checksum=get_hash(row), who=who,
                        blueprint=blueprint, associations=associations))

# print(courses)


def qualities(course_id):

    course_data = get_course(course_id)
    data = dict(course_id=course_id, error='')

    if not course_data.response_error:
        account = course_data.results[0]['account_id']
        data['is_blueprint'] = course_data.results[0]['blueprint']
        data['student_count'] = course_data.results[0]['total_students']
        child = get_child(account)
        if child:
            child = child[0]
        else:
            child = ''
        parent = get_parent(account)
        if parent:
            parent = parent[0]
            promote = True
        else:
            parent = ''
            promote = False
        data['accounts'] = dict(
            account=account, child=child, parent=parent, promote=promote)

    else:
        message = course_data.results[0]['errors'][0]['message']
        if message == 'The specified resource does not exist.':
            data['error'] = f"course {course_id} does not exist"
        else:
            data['error'] = message

    return data


def course_data(j):

    if not j['blueprint']:
        blueprint_error = ['no blueprint course specified']
        return dict(checksum=j['checksum'], who=j['who'], error=blueprint_error)
    else:
        blueprint_course_id = j['blueprint'][0]

    blueprint_qualities = qualities(blueprint_course_id)
    if blueprint_qualities['error']:
        return dict(checksum=j['checksum'], who=j['who'], error=[blueprint_qualities['error']])
    if blueprint_qualities['student_count'] != 0:
        return dict(checksum=j['checksum'], who=j['who'], error=[f"blueprint cannot have students [{blueprint_qualities['student_count']}]"])
    association_data = list(map(qualities, j['associations']))
    assocaition_errors = list(
        filter(lambda x: x, map(lambda x: x['error'], association_data)))
    if assocaition_errors:
        return dict(checksum=j['checksum'], who=j['who'], error=assocaition_errors)

    return dict(checksum=j['checksum'], who=j['who'], blueprint=blueprint_qualities, associations=association_data)


def organise_jobs(processed_jobs, job_list):
    processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
    job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))
    return [processed_jobs, job_list]


processed_jobs: list = []
job_list = list(map(course_data, courses))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)

# processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
# job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))

# test that the associations are in the right sub account (same or child of blueprint)
job_list = list(map(correct_subaccount, job_list))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)
# processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
# job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))

# test that no blueprint is being associate to a blueprint
job_list = list(map(valid_associations, job_list))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)
# processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
# job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))


for job in processed_jobs:
    print(job['checksum'], job['error'])
print(len(processed_jobs))


# job_list has no errors now
# create blueprints
job_list = list(map(create_blueprint2, job_list))
# associate courses
job_list = list(map(create_associations2, job_list))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)
# processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
# job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))
print(json.dumps(job_list, indent=4))
for job in processed_jobs:
    print(job['checksum'], job['error'], job['who']['name'])
    # print(job)
print(len(processed_jobs))
print(json.dumps(processed_jobs[9], indent=4))
write_data(processed_jobs)
exit()
