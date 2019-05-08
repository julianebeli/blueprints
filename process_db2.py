import __init__
from __init__ import here
import hashlib
import json
from pathlib import Path
from datetime import datetime
import re
from tests import get_course_id, get_hash, get_course, create_blueprint2, create_associations2, valid_associations, correct_subaccount, find_errors
from subaccount_info_reader import get_parent, get_child
from source_data import get_data, write_data
from mail import make_msg


def qualities(course_id):

    def get_error(r):
        if r.response_error:
            message = r.results[0]['errors'][0]['message']
            if message == 'The specified resource does not exist.':
                return f"course {course_id} does not exist"
            else:
                return message
        else:
            return None

    if not course_id:
        data = dict(course_id=None, error='No course specified', is_blueprint=False, student_count=0, accounts={})

    else:
        course_data = get_course(course_id)
        error = get_error(course_data)

        data = dict(course_id=course_id, error=error, is_blueprint=False, student_count=0, accounts={})

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

    # print(data)
    return data


def organise_jobs(processed_jobs, job_list):
    processed_jobs.extend(list(filter(lambda x: 'error' in x.keys(), job_list)))
    job_list = list(filter(lambda x: 'error' not in x.keys(), job_list))
    return [processed_jobs, job_list]


datafile = Path(here) / 'raw_data' / 'Blueprint Course Management 1 (14).xlsx'
rows = get_data(datafile)


courses = []
for row in rows:
    who = dict(date=row.Starttime, name=row.Name, email=row.Email, school=row.School, create_blueprint=row.CourseID,
               use_blueprint=row.UseexistingBlueprintcourse, associations=row.Coursestoassociate)
    blueprint = list(set(filter(lambda x: x, (get_course_id(row.CourseID)
                                              + get_course_id(row.UseexistingBlueprintcourse)))))
    blueprint = list(map(qualities, blueprint))
    associations = list(set(filter(lambda x: x, get_course_id(row.Coursestoassociate))))
    associations = list(map(qualities, associations))
    courses.append(dict(checksum=get_hash(row), who=who,
                        blueprint=blueprint, associations=associations))


processed_jobs: list = []
job_list = list(map(find_errors, courses))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)

# test that the associations are in the right sub account (same or child of blueprint)
job_list = list(map(correct_subaccount, job_list))
[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)

# test that no blueprint is being associate to a blueprint
job_list = list(map(valid_associations, job_list))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)


# job_list has no errors now
# create blueprints
job_list = list(map(create_blueprint2, job_list))
# associate courses
job_list = list(map(create_associations2, job_list))

[processed_jobs, job_list] = organise_jobs(processed_jobs, job_list)

print(len(processed_jobs))

list(map(make_msg, processed_jobs))
exit()
# print(json.dumps(processed_jobs[9], indent=4))
write_data(processed_jobs)
exit()
