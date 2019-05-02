import __init__
from api.requestor import API


cache_time = 60*60*24
api = API(server='prod', cache=None)


methodname = 'begin_migration_to_push_to_associated_courses'
# methodname = 'get_associated_course_information'
course_id = 58195
template_id = 'default'

params = dict(methodname=methodname,
              course_id=course_id,
              template_id=template_id)

api.add_method(**params)

api.do()

print(api.results)


