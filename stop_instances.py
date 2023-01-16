#!/usr/bin/python3

""" Stop EC2 Instance. """

# import sys
# import pprint
import argparse
import textwrap
import boto3
from aws_keys import AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


def prepare_arguments():
    """ Parse commandline arguments."""

    parser = argparse.ArgumentParser(
        prog='stop_instances.py',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent('''\
        Stop a bunch of AWS EC2 instance..

        Autor: Melanie Desaive <m.desaive@mailbox.org>
        '''),
        epilog=textwrap.dedent('''\
        Examples:

            ./stop_instance.py --instance="i-xxxxx,i-xxxx"
        '''))

    parser.add_argument(
        '-i', '--instances',
        dest='instances',
        help='Instances to stop.',
        required=True)
    args = parser.parse_args()

    return args


def main():
    """ main :) """
    args = prepare_arguments()
    instance_list = args.instances.split(',')

    ec2 = boto3.client(
        'ec2',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    ec2.stop_instances(InstanceIds=instance_list)


if __name__ == "__main__":
    main()
