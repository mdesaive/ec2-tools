#!/usr/bin/python3

""" Stops Minecraft VM if no users a logged in for a certain amount of time. """

import sys
import os
import subprocess
import time
import datetime
import pprint
import argparse
import textwrap
import re
import boto3
import ovh
from aws_keys import AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def prepare_arguments():
    """ Parse commandline arguments."""

    parser = argparse.ArgumentParser(
        prog='start_instances.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
        This script should usually be called from a timer (e.g. cron) in certain intervalls and stops
        a minecraft server after a certain period of time where no users are logged in.

        Autor: Melanie Desaive <m.desaive@mailbox.org>
        '''),
        epilog=textwrap.dedent('''\
        Examples:

            ./mc_idle_stopper.py --instance="i-xxxxx,i-xxxx"
        '''))

    parser.add_argument(
        '-i', '--instance-name',
        dest='instance_name',
        help='Instance name to stop.',
        required=True)
    parser.add_argument(
        '-t','--timeout',
        dest='timeout',
        help='Stop when no user was logged in after this timeout.',
        required=True)
    parser.add_argument(
        '--ovh-id',
        dest='ovh_record_id',
        help='OVH record id.',
        required=True)
    parser.add_argument(
        '--dns-target',
        dest='dns_target',
        help='OVH DNS target',
        required=True)
    parser.add_argument(
        '--dns-subdomain',
        dest='dns_subdomain',
        help='OVH DNS subdomain',
        required=True)
    parser.add_argument(
        '-d', '--dry-run',
        dest='dry_run',
        help='Do dry run do not really stop.',
        action='store_true',
        required=False)
    args = parser.parse_args()

    return args


def get_all_instance():
    """ Read all instances from our region."""
    ec2 = boto3.client(
        'ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    return ec2.describe_instances()["Reservations"]


def map_instance_ids_to_names(all_instances):
    """ Create simple dictionary mapping names to ids."""
    instance_name_mapping = []
    for my_instance_list in all_instances:
        # pprint.pprint(my_instance["Instances"][0]["State"]["Name"])
        for my_instance in my_instance_list["Instances"]:
            record = {}
            record["instance_id"] = my_instance["InstanceId"]
            record["instance_name"] = list(filter(lambda x: x["Key"] == "Name", my_instance["Tags"]))[0]["Value"]
            record["state"] = my_instance["State"]["Name"]
            instance_name_mapping.append(record)
    return instance_name_mapping


def stop_instances(instance_id):
    ec2 = boto3.client(
        'ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    ec2.stop_instances(InstanceIds=instance_id)


def main():
    """ main :) """
    args = prepare_arguments()

    timeout = int(args.timeout)

    all_instances = get_all_instance()
    # pprint.pprint(all_instances)
    instance_name_mapping = map_instance_ids_to_names(all_instances)
    # pprint.pprint(instance_name_mapping)

    instance_name = args.instance_name

    # pprint.pprint(instance_name)
    if instance_name not in [ x["instance_name"] for x in instance_name_mapping ]:
       # pprint.pprint(instance_name_mapping)
       sys.exit(f'Instance with name=\"{instance_name}\" not available.')

    # pprint.pprint(instance_name)

    print(f'Query list of online players in screen.')
    cmd = 'su -c "screen -d -R minecraft -X stuff \\"list \r\\"" minecraft'
    # print(f'{cmd}\n')
    list_players = subprocess.check_output(cmd, shell=True)
    
    try:
        cmd = 'grep "\[Server thread/INFO\]: There are .* of .* players online" /opt/paper/run/logs/latest.log'
        num_players = subprocess.check_output(cmd, shell=True)
    except subprocess.CalledProcessError as grepexc:                                                                                                   
       if grepexc.returncode == 1:
           sys.exit('Error - no info about players')
       else:
           sys.exit(f'Grep error, returncode = {grepexc.returncode}, error = {grepexc.output}')

    num_players_list = num_players.splitlines()
    last_num_player = num_players_list[len(num_players_list) - 1]
    result = re.search('\[[\d\:]*\] \[Server thread/INFO\]: There are ([\d]*) of a max of [\d]* players online: .*.*$', last_num_player.decode("utf-8"))
    num_online = int(result.group(1))

    print(f'Currently {num_online} players are online.')

    if num_online == 0:
        print('\nChecking last logout time...')
        try:
            cmd = '/bin/grep "left the game" /opt/paper/run/logs/latest.log'
            logouts = subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError as grepexc:                                                                                                   
            if grepexc.returncode == 1:
                print('No logouts at all, checking start time of server')
                try:
                    cmd = 'grep "\[Server thread/INFO\]: Preparing level" /opt/paper/run/logs/latest.log'
                    start_server_log = subprocess.check_output(cmd, shell=True)
                except subprocess.CalledProcessError as grepexc:                                                                                                   
                   if grepexc.returncode == 1:
                       sys.exit('Error - no info about start server')
                   else:
                       sys.exit(f'Grep error, returncode = {grepexc.returncode}, error = {grepexc.output}')

                start_server_list = start_server_log.splitlines()
                # pprint.pprint(start_server_list)
                last_start_server = start_server_list[len(start_server_list) - 1]
                result = re.search("\[([\d\:]*)\].*$", last_start_server.decode("utf-8"))

                timestamp = result.group(1)
                # print(timestamp)
            else:
                sys.exit(f'Grep error, returncode = {grepexc.returncode}, error = {grepexc.output}')
        else:
            logouts_list = logouts.splitlines()
            last_logout = logouts_list[len(logouts_list) - 1]
    
            result = re.search("\[([\d\:]*)\].*$", last_logout.decode("utf-8"))
    
            timestamp = result.group(1)
            
            # print(timestamp)

    time_datetime = datetime.datetime.strptime(timestamp,'%H:%M:%S')
    idle = datetime.datetime.now() - time_datetime

    idle_minutes = round( idle.seconds / 60 )

    print(f'Server is idle for {idle_minutes} minutes.')
    cmd = f'su -c "screen -d -R minecraft -X stuff \\"say No users online for {idle_minutes} minutes.\r\\"" minecraft'
    # print(f'{cmd}\n')
    subprocess.check_output(cmd, shell=True)

    if idle_minutes > timeout:
        instance =  list(filter(lambda x: x["instance_name"] == instance_name, instance_name_mapping))[0]
        # pprint.pprint(instance)
        print(f'Stopping instance {instance["instance_id"]} / {instance["instance_name"]}.')
        cmd = f'su -c "screen -d -R minecraft -X stuff \\"say Stopping server {instance["instance_id"]} / {instance["instance_name"]}.\r\\"" minecraft'
        # print(f'{cmd}\n')
        subprocess.check_output(cmd, shell=True)
        client = ovh.Client()
        target = args.dns_target
        subdomain = args.dns_subdomain
        ovh_record_id = args.ovh_record_id
        print(f'Setting OVH record {ovh_record_id} to subdomain {subdomain} with target {target}')

    #     cmd = f'su -c "screen -d -R minecraft -X stuff \\"save-all\r\\"" minecraft'
    #     # print(f'{cmd}\n')
    #     subprocess.check_output(cmd, shell=True)

    #     cmd = f'su -c "screen -d -R minecraft -X stuff \\"stop\r\\"" minecraft'
    #     # print(f'{cmd}\n')
    #     subprocess.check_output(cmd, shell=True)

    #     time.sleep(15)

        cmd = 'systemctl stop minecraft.service'       
        subprocess.check_output(cmd, shell=True)

        if not args.dry_run:
            client.put(
                f'/domain/zone/desaive.de/record/{ ovh_record_id }',
                subDomain=subdomain,
                target=target,
                ttl=60)
            client.post('/domain/zone/desaive.de/refresh')
            stop_instances([instance["instance_id"], ])



    

if __name__ == "__main__":
    main()
