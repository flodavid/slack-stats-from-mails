import imaplib
import email
import os
import re
from datetime import date
from yaml import load
from bs4 import BeautifulSoup
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
from pprint import pprint

data = load(open('params.yml', 'r'), Loader=Loader)

# Google
FROM_EMAIL  = data['email']['username']
FROM_PWD    = data['email']['password']
SMTP_SERVER = data['email']['smtp-server']
SMTP_PORT   = data['email']['smpt-port']

print('Connecting to IMAP server')
mail=imaplib.IMAP4_SSL(SMTP_SERVER, SMTP_PORT)
print('Logging to mail box')
mail.login(FROM_EMAIL,FROM_PWD)
print('Selecting')
nb_mail = mail.select("Slack")
print('You\'ve got '+ str(nb_mail[1]) + ' mails')
print('Listing emails')
mail_list = mail.list()

print('Searching for mail with subject')
typ, msgs = mail.search(None, 'ALL')
msgs = msgs[0].split()

# Open CSV file where the result will be stored
today = date.today()
csv= open(data['slack']['name']+"-stats_"+str(today)+".csv","w")
print ("Date , Messages, Public, Private, Direct, Files ,")
print ("Date , Messages, Public, Private, Direct, Files ,", file=csv)

# handle each email
for emailid in msgs:
    resp, data = mail.fetch(emailid, "(RFC822)")
    raw_email = data[0][1].decode('utf-8')
    email_content = email.message_from_string(raw_email)
    # Get html email body (It's second part. Frst part of payload is plain text)
    html_content = email_content.get_payload()[1]
    date_retrieved = False
    parse_success = False

    # Decode if necessary
    if html_content['Content-Transfer-Encoding'] == "base64":
        msg = html_content.get_payload(decode=True)
    else:
        msg = html_content.get_payload(decode=False)

    #print(msg)
    # Create html tree from email body
    html_soup = BeautifulSoup(msg, "html.parser")
    #print(html_soup.prettify())
    title = html_soup.find("title")
    
    if title != None:
        date_retrieved = True
        report_date = '"' + title.text.split('the week of ')[1].split("</title>")[0].replace('st', '').replace('nd', '').replace('rd', '').replace('th', '') + '"'

    #./body/table/tr/td/center/table/tr/td/div/p
    lines = html_soup.find_all('p')
    #print("LINES:", lines)
    for line in lines:
        text = str(line).strip()
        if " sent a total of <strong>" in text:
            parse_success = True
            
            # Separate each number
            list_msg_nb = text.split("<strong>")

            # After separation: 
# \t\tYour team
# 2,491 messages</strong> last week (that\'s 859 fewer than the week before). \t\t\t\t\t\tOf those,
# 57% were in public channels</strong>, 
# 8% were in private channels</strong>, and 
# 35% were direct messages</strong>. \t\t\t\t\t\t\t\t\t\tYour team also uploaded 
# 24 files</strong> (that\'s 18 fewer than the week before). \t\t\t\t\t</p>\r
            #
            msg_nb = list_msg_nb[1].split(" messages")[0].replace(',', '')
            public, private, direct, files = '0000'
            # Get public percentage
            if len(list_msg_nb) > 2:
                public =    list_msg_nb[2].split(" were")[0]
            # Get private percentage
            if len(list_msg_nb) > 3:
                private =   list_msg_nb[3].split(" were")[0]
            # Get DM percentage and number of files
            if len(list_msg_nb) > 4:
                # We can get both mentioned
                if len(list_msg_nb) > 5:
                    files =     list_msg_nb[5].split(" file")[0]
                    direct =    list_msg_nb[4].split(" were")[0]
                # Get either DM percentage or number of files
                else:
                    if "file" in list_msg_nb[4]:
                        files =     list_msg_nb[4].split(" file")[0]
                    elif "were" in list_msg_nb[4]:
                        direct =    list_msg_nb[4].split(" were")[0]        
                    else:
                        print("Unknown date in:", list_msg_nb[4])

            # Print the final result in console and file
            csv_line = report_date + ', ' + msg_nb + ', ' + public + ', ' + private + ', ' + direct + ', ' + files + ', '
            print(csv_line)
            print(csv_line, file=csv)

    # Try to parse it with the new format
    if not parse_success:
        
        for line in lines:
            # Examples :
            # \t\tYour team sent a total of <strong>2,491 messages</strong> last week (that\'s 859 fewer than the week before). \t\t\t\t\t\tOf those, <strong>57% were in public channels</strong>, <strong>8% were in private channels</strong>, and <strong>35% were direct messages</strong>. \t\t\t\t\t\t\t\t\t\tYour team also uploaded <strong>24 files</strong> (that\'s 18 fewer than the week before). \t\t\t\t\t</p>\r
            # Your team sent a total of 2,491 messages last week (that\'s 859 fewer\r
            if "Your members " in line:
                treat_success = True
                print(">>>LINE IS:", line)

    # It still not parsed, then it failed
    if not parse_success:
        if date_retrieved:
            print("Failed to parse email of", report_date, email_content['Date'] )
        else:
            print("Failed to parse email content and date;", email_content['Date'] )

csv.close()