import __init__
import re
from api.requestor2 import API
import hashlib
from datetime import datetime
from pluck import pluck
import json


cache_time = 24 * 60 * 60 * 1
api = API('prod', cache= cache_time)
course_id_stem = re.compile(r"/courses/(\d+)")
course_id_number = re.compile(r"^(\d+)$")


def get_hash(r):
    row = list(map(str, list(r._asdict().values())[:-3]))
    print(row)
    m = hashlib.md5()
    s = []
    for e in row:
        s.append(''.join(e))
    m.update(''.join(s).encode())
    chksum = m.hexdigest()
    # print(chksum)
    return chksum


def get_dates(row):
    def make_dt(T):
        print(f"T: {T}")
        (d, t) = T.split(' ')
        [month, day, year] = list(map(int, d.split('/')))
        [hour, minute] = list(map(int, t.split(':')))[:2]

        return datetime(year + 2000, month, day, hour, minute)

    start = make_dt(row.Starttime)
    end = make_dt(row.Completiontime)
    diff = end - start
    return {'start': start.date(), 'duration': diff}


def get_course_id(u):
    # print(u, course_id.findall(u))
    if not u:
        return [u]
    else:
        return course_id_stem.findall(u) + course_id_number.findall(u)


def blueprint_id(row):
    courses = get_course_id(getattr(row, 'CourseID')) + \
        get_course_id(getattr(row, 'UseexistingBlueprintcourse'))
    return list(map(lambda y: int(y), filter(lambda x: x, courses)))


def association_ids(row):
    courses = get_course_id(getattr(row, 'Coursestoassociate'))
    return list(map(lambda y: int(y), filter(lambda x: x, courses)))


def get_course(course_id):
    # print(f'course data for {course_id}')
    # get course data or get error
    methodname = 'get_single_course_courses'
    params = {'methodname': methodname, 'id': course_id, 'include': ['total_students']}
    api.add_method(**params)
    api.do()
    # print(f'API RESPONSE:\n{api.results}')
    # print(f'{"_" * 48}')
    return api


def find_errors(job):
    blueprint = job['blueprint']
    if not blueprint:
        job.update(error=['no blueprint course specified'])
        return job
    if len(blueprint) > 1:
        job.update(error=['More than 1 blueprint course specified'])
    blueprint = blueprint[0]
    if blueprint['error']:
        job.update(error=[blueprint['error']])
        return job
    if blueprint['student_count'] != 0:
        job.update(dict(error=[f"blueprint cannot have students [{blueprint['student_count']}]"]))
        return job

    assocaition_errors = list(
        filter(lambda x: x, map(lambda x: x['error'], job['associations'])))
    if assocaition_errors:
        job.update(dict(error=assocaition_errors))
        return job

    # j.update(dict(blueprint=blueprint_qualities, associations=association_data))
    return job


def get_associated_course_information(course_id):
    methodname = 'get_associated_course_information'
    params = {'methodname': methodname, 'course_id': course_id[0], 'template_id': 'default'}
    api.add_method(**params)
    api.do()
    associated = pluck(api.results, 'id')
    # this failed on a 'course does not exist' error
    # it happens if you have not promoted the course to blueprint and ask for associations
    return associated


def get_subaccounts(account):
    methodname = 'get_sub_accounts_of_account'
    params = {'methodname': methodname, 'account_id': account, 'recursive': True}
    api.add_method(**params)
    api.do()
    accounts = []
    for subaccount in api.results:
        accounts.extend([subaccount['id'], subaccount['parent_account_id']])

    return set(accounts)


def correct_subaccount(job):
    blueprint_accounts = job['blueprint'][0]['accounts']
    valid_accounts = set(filter(lambda x: type(x) is int, blueprint_accounts.values()))
    association_accounts = set(map(lambda x: x['accounts']['account'], job['associations']))
    if not association_accounts.issubset(valid_accounts):
        job.update(dict(error=['association courses are not in the right subaccount']))
    return job


def valid_associations(job):
    association_blueprints = [x['is_blueprint'] for x in job['associations'] if x['is_blueprint']]
    if association_blueprints:
        job.update(dict(error=['association courses contain a blueprint course']))
    return job


def create_blueprint(job):
    # 'blueprint': {'course_id': '43450', 'error': '', 'is_blueprint': True, 'student_count': 0, 'accounts': {'account': 366, 'child': 367, 'parent': '', 'promote': False}}

    # options: make blueprint, promote
    # print("blueprint2")
    # print(json.dumps(job,indent=4))
    work_to_do = False
    params = {
        'methodname': "update_course",
        'id': job['blueprint'][0]['course_id']
    }
    if not job['blueprint'][0]['is_blueprint']:
        params.update({"course[blueprint]": True})
        work_to_do = True

    if job['blueprint'][0]['accounts']['promote']:
        params.update({"course[account_id]": job['blueprint'][0]['accounts']['parent']})
        work_to_do = True

    if work_to_do:
        api.add_method(**params)
        api.do()
        job.update(dict(error=['Blueprint course created']))
    else:
        job.update(dict(error=['The blueprint course already exists']))

    return job


def create_associations(job):
    # print(f"creating associations with {blueprint}, {associations}")
    current_error = job['error']

    blueprint = job['blueprint'][0]['course_id']
    associations = list(map(lambda x: x['course_id'], job['associations']))
    if associations:
        # could look for already associated but ultimately this is another api call
        params = dict(methodname='update_associated_courses',
                      course_id=blueprint,
                      template_id='default',
                      course_ids_to_add=associations
                      )
        # print(params)
        api.add_method(**params)
        api.do()
        # print('api results', api.results)

        # force sync
        methodname = 'begin_migration_to_push_to_associated_courses'
        params = dict(methodname=methodname,
                      course_id=blueprint,
                      template_id='default')
        # print(params)
        api.add_method(**params)
        api.do()
        # print('api results', api.results)

        current_error.append('associations complete')
        job['error'] = current_error
    else:
        current_error.append('nothing to associate')
        job['error'] = current_error

    return job





if __name__ == '__main__':
    pass
