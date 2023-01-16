#!/usr/bin/python3

""" Start or stop EC2 Instance. """

import sys
import pprint
import argparse
import textwrap
import boto3
from aws_keys import AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def prepare_arguments():
    """ Parse commandline arguments."""

    parser = argparse.ArgumentParser(
        prog='start_instances.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
        Start a bunch of AWS EC2 instance..

        Autor: Melanie Desaive <m.desaive@mailbox.org>
        '''),
        epilog=textwrap.dedent('''\
        Examples:

            ./start_instance.py --instance="i-xxxxx,i-xxxx"
        '''))

    parser.add_argument(
        '-i', '--instances',
        dest='instances',
        help='Instances to start.',
        required=True)
    parser.add_argument(
        '--start',
        dest='start',
        help='Start the named instances.',
        action='store_true',
        required=False)
    parser.add_argument(
        '--stop',
        dest='stop',
        help='Stop the named instances.',
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


def start_instances(instance_id_list):
    ec2 = boto3.client(
        'ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    ec2.start_instances(InstanceIds=instance_id_list)

def stop_instances(instance_id_list):
    ec2 = boto3.client(
        'ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    ec2.stop_instances(InstanceIds=instance_id_list)


def main():
    """ main :) """
    args = prepare_arguments()

    if not args.start and not args.stop:
        sys.exit("Do either give \"--start\" or \"--stop\" parameter!")
    all_instances = get_all_instance()
    # pprint.pprint(all_instances)
    instance_name_mapping = map_instance_ids_to_names(all_instances)

    instance_name_list = args.instances.split(',')

    instance_id_list = []
    # pprint.pprint(instance_name_list)
    for name in instance_name_list:
        if name not in [ x["instance_name"] for x in instance_name_mapping ]:
            pprint.pprint(instance_name_mapping)
            sys.exit(f'Instance with name=\"{name}\" not available.')
        instance_id_list.append(list(filter(lambda x: x["instance_name"] == name, instance_name_mapping))[0]["instance_id"])

    pprint.pprint(instance_id_list)
    if args.start:
        start_instances(instance_id_list)
    if args.stop:
        stop_instances(instance_id_list)


if __name__ == "__main__":
    main()
