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
        blueprint_error = 'no blueprint course specified'
        return dict(checksum=j['checksum'], error=blueprint_error)
    else:
        blueprint_course_id = j['blueprint'][0]

    blueprint_qualities = qualities(blueprint_course_id)
    if blueprint_qualities['error']:
        return dict(checksum=j['checksum'], error=blueprint_qualities['error'])
    association_data = list(map(qualities, j['associations']))
    assocaition_errors = list(filter(lambda x: x, map(lambda x: x['error'], association_data)))
    if assocaition_errors:
        return dict(checksum=j['checksum'], error=assocaition_errors)

    return dict(checksum=j['checksum'], blueprint=blueprint_qualities, associations=association_data)


job_list = list(map(course_data, jobs))
# print(job_list[0:10])
undoable_jobs = []
undoable_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
print(undoable_jobs)

job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))

# for job in job_list:
#     print(job)
# print(job_list[0])
# for job in job_list:
#     try:
#         account = job['blueprint']['course_subaccount']
#         blueprint_parent = get_parent(account)
#         # print(account, blueprint_parent)
#         if blueprint_parent:
#             print("promoting this job")
#             job['blueprint'].update(
#                 dict(promote=True, parent_subaccount=blueprint_parent[0]))
#             print(job)

#     except:
#         job.update(error=job['blueprint']['error'])
# undoable_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
# print(undoable_jobs)
# job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))
# print(len(job_list))

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
