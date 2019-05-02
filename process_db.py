import __init__
import hashlib
import json
from db_reader import db_reader
from api.requestor import API
from datetime import datetime

now = str(datetime.now())
print(now)

cache_time = 60*60*24
api = API(server='prod', cache=None)
data = db_reader('data.db', 'requests')
# print(data)

rows = [data.nt(*x) for x in data.connection.cursor.execute(data.sql_select)]
rows = [x for x in rows if not x.Completed]


def get_course_id(url):  # trailing slash error?
    return url.split('/')[-1]


def get_hash(row):
    m = hashlib.md5()
    s = []
    for e in (row._asdict().items()):
        s.append(''.join(e))

    m.update(''.join(s).encode())
    chksum = m.hexdigest()
    print(chksum)
    return chksum


def get_course(course_id):
    methodname = "get_single_course_courses"
    params = {'methodname': methodname, 'id': course_id}
    api.add_method(**params)
    api.do()
    return api.results


def createBluePrint(row):
    # recipe to move and promote course
    # get course subaccount GET /api/v1/courses/:id
    # get subaccount parent GET /api/v1/accounts/:id
    # move course to parent subaccount PUT /api/v1/courses/:id course[account_id]       integer     The unique ID of the account to move the course to.
    # make blueprint PUT /api/v1/courses/:id    course[blueprint]      boolean     Sets the course as a blueprint course. NOTE: The Blueprint Courses feature is in beta

    course_id = get_course_id(row.CourseID)
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
    print(account_id, is_blueprint)

    methodname = "get_single_account"
    account_id = account_id
    params = {'methodname': methodname, 'id': account_id}
    api.add_method(**params)
    api.do()
    account_data = api.results
    # print(json.dumps(account_data, indent=4))
    manual_account = '*' in account_data[0]['name']
    print(f'Is manual account: {manual_account}')
    if manual_account:
        new_account_id = account_data[0]['parent_account_id']
    else:
        new_account_id = account_id
    # account_parent =
    # print(account_parent)

    methodname = "update_course"
    params = {'methodname': methodname,
              'id': course_id,
              "course[account_id]": new_account_id,
              "course[blueprint]": True}
    api.add_method(**params)
    api.do()
    # print(json.dumps(api.results, indent=4))
    print()
    return


def createAssociation(row):
    '''
    row is either associating to a new blueprint or a courseid
    but not both. The filter picks the one that's present
    association_data = {blueprint_course_id,[associated_course_ids]}
    '''

    association_data = [get_course_id(list(filter(lambda y: y, [row.CourseID,
                                                                row.UseexistingBlueprintcourse]))[0]),
                        list(map(get_course_id, row.Coursestoassociate.split('\n')))]

    print(f'Association data: {association_data}')
    course_data = get_course(association_data[0])
    if not course_data[0]['blueprint']:
        return
    # recipe to associate courses to a blueprint
    # get bluprint course id
    # get course ids for associations
    # method to use: 'Update associated courses'
    # PUT /api/v1/courses/:course_id/blueprint_templates/:template_id/update_associations
    # Parameter       Type    Description
    # course_ids_to_add       Array   Courses to add as associated courses
    print('_' * 48)
    print(association_data, len(association_data[1][0]))
    print('len check', len(association_data[1]) > 0)
    if association_data[1] != ['']:
        print('There is association data')
    else:
        print('There is NOT association data')

    if association_data[1] != ['']:
        methodname = 'update_associated_courses'
        params = dict(methodname=methodname,
                      course_id=association_data[0],
                      template_id='default',
                      course_ids_to_add=association_data[1]
                      )
        # print(json.dumps(params, indent=4))
        api.add_method(**params)
        api.do()
    # print(json.dumps(api.results, indent=4))

    # force sync
    methodname = 'begin_migration_to_push_to_associated_courses'
    params = dict(methodname=methodname,
                  course_id=association_data[0],
                  template_id='default')
    api.add_method(**params)
    api.do()
    print(api.results)
    print()
    return


def mark_row_complete(row, the_date):
    # for r in data.connection.cursor.execute(f"select * from requests where Starttime='{row.Starttime}'"):
    #     print(r)
    cmd = f"update requests set Completed='{the_date}' where Starttime='{row.Starttime}'"
    print(cmd)
    data.connection.cursor.execute(cmd)
    data.connection.connect.commit()
    return


def strip_lower(t):
    return t.strip().lower()


# print(rows)
for row in rows:
    print()
    # chksum = get_hash(row)

    if (f'{strip_lower(row.CreatenewBlueprintcourse)}{strip_lower(row.AttachtoBlueprintcourse)}' != "nono"):
        if strip_lower(row.CreatenewBlueprintcourse) == "yes":
            createBluePrint(row)
        createAssociation(row)
    mark_row_complete(row, now)
# exit()


# make_blueprint_requests = [x for x in rows if x.CreatenewBlueprintcourse == 'Yes']
# make_blueprint_data = []
# for entry in make_blueprint_requests:
#     make_blueprint_data.append(get_course_id(entry.CourseID))

# print(make_blueprint_data)

# associate_blueprint_data = [[get_course_id(list(filter(lambda y: y, [x.CourseID,
#                                                                      x.UseexistingBlueprintcourse]))[0]),
#                              list(map(get_course_id, x.Coursestoassociate.split('\n')))]
#                             for x in rows if x.Coursestoassociate]
# print(associate_blueprint_data)


# exit()
# # https://tas.beta.instructure.com/courses/42852
# make_blueprint_data = ['42852']


# # recipe to associate courses to a blueprint
# # get bluprint course id
# # get course ids for associations
# # method to use: 'Update associated courses'
# # PUT /api/v1/courses/:course_id/blueprint_templates/:template_id/update_associations
# # Parameter       Type    Description
# # course_ids_to_add       Array   Courses to add as associated courses

# methodname = 'update_associated_courses'
# for entry in associate_blueprint_data:
#     params = dict(methodname=methodname,
#                   course_id=entry[0],
#                   template_id='default',
#                   course_ids_to_remove=entry[1]
#                   )
#     print(json.dumps(params, indent=4))
#     api.add_method(**params)
#     api.do()
#     print(json.dumps(api.results, indent=4))


# for row in rows:
#     chksum = check(row)
#     if CreatenewBlueprintcourse is "Yes":
#         createBluePrint(row)
#     createAssociation(row)
#     mark_row_complete(row)

# if __name__ == '__main__':
#     course_data = get_course('10234')
#     course_data = get_course('99999')


# check that the course url exists
# check for students in course before template making
