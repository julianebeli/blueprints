
from smtplib import SMTP
from email.message import EmailMessage

import mail_config as config


def send_mail(msg):

    with SMTP(config.smtpserver) as smtp:
        # smtp.noop()
        smtp.send_message(msg)
    print()


def compose_mail(job):
    pass


def make_msg(job):
    # print('_' * 48)
    email_to = (job['who']['email'])
    msg = EmailMessage()
    msg['Subject'] = 'blueprint request'
    # # me == the sender's email address
    # # family = the list of all recipients' email addresses
    msg['From'] = config.email_from
    msg['To'] = config.email_to
    # msg['Cc'] = 'julian.email@protonmail.com'
    # msg.preamble = 'Our family reunion'

    if job['who']['create_blueprint']:
        blueprint_request = job['who']['create_blueprint']
        blueprint_script = f"You asked to create a blueprint course."
        association_request = ''

        if job['who']['associations']:
            blueprint_script = f"You asked to create a blueprint course and associate it to some courses."
            blueprint_request = job['who']['create_blueprint']
            association_request = job['who']['associations']
    else:
        blueprint_request = job['who']['use_blueprint']
        blueprint_script = f"You asked to associate an exising blueprint to some courses."

    # print(f">{blueprint_request}<")
    try:
        blueprint_request = blueprint_request.strip()
    except:
        pass
    # print(f">{blueprint_request}<")

    try:
        blueprint_course = job['blueprint'][0]['course_id']
    except IndexError:
        blueprint_course = []
    try:
        association_courses = list(map(lambda x: x['course_id'], job['associations']))
    except IndexError:
        association_courses = []

    if not job['who']['associations']:
        assoc_msg = ''
    else:
        arequest = job['who']['associations']
        if 'associations' not in job.keys():
            assoc_msg = f"The associations you specified were\n{arequest}\nThis was interpreted as course id(s): {[]}"
        else:
            assoc_msg = f"The associations you specified were\n{arequest}\nThis was interpreted as course id(s): {association_courses}"

    message = f"""Hi {job['who']['name']} ({email_to}),
On {job['who']['date'].split(' ')[0]} we processed a request from you.
{blueprint_script}

The blueprint you specified was: {blueprint_request}
This was interpreted as course id: {blueprint_course}

{assoc_msg}

The processing result was:
{", ".join(list(map(lambda x: x.capitalize(),job['error'])))}

"""


    msg.set_content(message)

    # print(dir(msg))
    # print(msg.values())
    # exit()
    send_mail(msg)


if __name__ == '__main__':

    pass
