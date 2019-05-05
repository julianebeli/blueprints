import __init__
import re
from api.requestor2 import API
import hashlib
from datetime import datetime
from pluck import pluck
import json


cache_time = 24 * 60 * 60 * 1
api = API('beta', cache=cache_time)
course_id_stem = re.compile(r"/courses/(\d+)")
course_id_number = re.compile(r"^(\d+)$")


def get_hash(r):
    row = list(r._asdict().items())[:-3]
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
    params = {'methodname': methodname, 'id': course_id, 'include': 'total_students'}
    api.add_method(**params)
    api.do()
    # print(f'API RESPONSE:\n{api.results}')
    # print(f'{"_" * 48}')
    return api


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
    blueprint_accounts = job['blueprint']['accounts']
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


def create_blueprint2(job):
    # 'blueprint': {'course_id': '43450', 'error': '', 'is_blueprint': True, 'student_count': 0, 'accounts': {'account': 366, 'child': 367, 'parent': '', 'promote': False}}

    # options: make blueprint, promote

    params = {
        'methodname': "update_course",
        'id': job['blueprint']['course_id']
    }
    if not job['blueprint']['is_blueprint']:
        params.update({"course[blueprint]": True})

    if job['blueprint']['accounts']['promote']:
        params.update({"course[account_id]": job['blueprint']['accounts']['parent']})

    pk = params.keys()

    if ("course[account_id]" in pk) or ("course[blueprint]" in pk):

        api.add_method(**params)
        api.do()
        job.update(dict(error=['Blueprint course created']))
    else:
        job.update(dict(error=['The blueprint course already exists']))

    return job


def create_associations2(job):
    # print(f"creating associations with {blueprint}, {associations}")
    current_error = job['error']

    blueprint = job['blueprint']['course_id']
    associations = list(map(lambda x: x['course_id'], job['associations']))
    if associations:
        params = dict(methodname='update_associated_courses',
                      course_id=blueprint,
                      template_id='default',
                      course_ids_to_add=associations
                      )
        # print(params)
        api.add_method(**params)
        api.do()

        # force sync
        methodname = 'begin_migration_to_push_to_associated_courses'
        params = dict(methodname=methodname,
                      course_id=blueprint,
                      template_id='default')
        # print(params)
        api.add_method(**params)
        api.do()

        current_error.append('associations complete')
        job['error'] = current_error
    else:
        current_error.append('nothing to associate')
        job['error'] = current_error

    return job


def create_blueprint(row):
    # recipe to move and promote course
    # get course subaccount GET /api/v1/courses/:id
    # get subaccount parent GET /api/v1/accounts/:id
    # move course to parent subaccount PUT /api/v1/courses/:id course[account_id]       integer     The unique ID of the account to move the course to.
    # make blueprint PUT /api/v1/courses/:id    course[blueprint]      boolean     Sets the course as a blueprint course. NOTE: The Blueprint Courses feature is in beta

    course_id = row[0]
    print(f'Creating Blueprint: {course_id}')

    # methodname = "get_single_course_courses"
    # params = {'methodname': methodname, 'id': course_id}
    # api.add_method(**params)
    # api.do()
    # course_data = api.results
    course_data = get_course(course_id)
    # print(json.dumps(course_data, indent=4))
    account_id = course_data[0]['account_id']
    is_blueprint = course_data[0]['blueprint']
    # print(account_id, is_blueprint)

    methodname = "get_single_account"
    account_id = account_id
    params = {'methodname': methodname, 'id': account_id}
    api.add_method(**params)
    api.do()
    account_data = api.results
    # print(json.dumps(account_data, indent=4))
    manual_account = '*' in account_data[0]['name']
    # print(f'Is manual account: {manual_account}')
    if manual_account:
        new_account_id = account_data[0]['parent_account_id']
    else:
        new_account_id = account_id
    print(f'new account id {new_account_id}')
    # account_parent =
    # print(account_parent)
    print('moving course to parent subaccount')
    methodname = "update_course"
    params = {'methodname': methodname,
              'id': course_id,
              "course[account_id]": new_account_id,
              "course[blueprint]": True}
    api.add_method(**params)
    api.do()
    print(json.dumps(api.results, indent=4))
    print()
    return api.results


def create_associations(blueprint, associations):
    print(f"creating associations with {blueprint}, {associations}")

    methodname = 'update_associated_courses'
    params = dict(methodname=methodname,
                  course_id=blueprint,
                  template_id='default',
                  course_ids_to_add=associations
                  )

    api.add_method(**params)
    api.do()
    print(f'association result: {api.results}')

    # force sync
    methodname = 'begin_migration_to_push_to_associated_courses'
    params = dict(methodname=methodname,
                  course_id=blueprint,
                  template_id='default')
    api.add_method(**params)
    api.do()


# [
#     {'errors': [
#         {'message': 'The specified resource does not exist.'}
#     ]
#     }
# ]

# [
#     [
#         {'id': 30951, 'name': '10 Maths Master', 'account_id': 202, 'uuid': 'gWRB08i8EglSuu23l8YdBmNo2ONToXcm0EzJ1c5q', 'start_at': None, 'grading_standard_id': None, 'is_public': None, 'created_at': '2018-01-18T23:18:42Z', 'course_code': '10MASTER', 'default_view': 'modules', 'root_account_id': 1, 'enrollment_term_id': 35, 'end_at': None, 'public_syllabus': False, 'public_syllabus_to_auth': False, 'storage_quota_mb': 500, 'is_public_to_auth_users': False,
#          'hide_final_grades': False, 'apply_assignment_group_weights': False, 'total_students': 0, 'calendar': {'ics': 'https://tas.instructure.com/feeds/calendars/course_gWRB08i8EglSuu23l8YdBmNo2ONToXcm0EzJ1c5q.ics'}, 'time_zone': 'Australia/Hobart', 'blueprint': True, 'blueprint_restrictions': {'content': True}, 'sis_course_id': None, 'sis_import_id': None, 'integration_id': None, 'enrollments': [], 'workflow_state': 'unpublished', 'restrict_enrollments_to_course_dates': False}
#     ]
# ]


if __name__ == '__main__':
    bluprint = 'https://tas.instructure.com/courses/41681'
    bluprint = 'https://tas.instructure.com/courses/52045'
    print(get_course_id(bluprint)[0])
    blueprint_data = get_course(get_course_id(bluprint)[0])
    print(json.dumps(blueprint_data, indent=4))
    print(is_error(blueprint_data))
    # exit()
    # subaccounts = get_subaccounts(blueprint_data[0]['account_id'])
    # print(subaccounts)
    courses = ['https://tas.instructure.com/courses/56657',
               'https://tas.instructure.com/courses/56780',
               'https://tas.instructure.com/courses/56657',
               'https://tas.instructure.com/courses/57895',
               'https://tas.instructure.com/courses/57519',
               'https://tas.instructure.com/courses/59450']
    course_data = list(map(lambda y: int(y[0]), filter(lambda x: x, map(get_course_id, courses))))

    data = list(map(get_course, course_data))
    print(json.dumps(data, indent=4))
    print(f"error data? {is_error(data[0])}")
    for d in data:
        # print(json.dumps(d, indent=4))
        print(is_error(d))
    account_ids = set(map(lambda x: x[0]['account_id'], data))
    # print(account_ids)
    # print(account_ids <= subaccounts)
