#!/usr/bin/env python3
import requests
import json
import urllib3
import os
import argparse


# SUPPRESS WARNINGS ############################################################
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# DOWNGRADE SSL ################################################################
from requests.packages.urllib3.contrib import pyopenssl
def downgrade_ssl():
    pyopenssl.DEFAULT_SSL_CIPHER_LIST = 'HIGH:RSA:!DH'
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS = 'HIGH:RSA:!DH'


# CONSTANTS ####################################################################
OUTPUT_DIR = './output/'
RECOVER_LAST_BUILD_ONLY = True
RECOVER_FROM_FAILURE = False
DEBUG = False


# UTILS ########################################################################
def print_debug(data):
    if DEBUG is True:
        print(data)


def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


# SAVERS #######################################################################
def dump_to_disk(url, consoleText, envVars):
    # first, need to create dirs
    folder = OUTPUT_DIR + url.replace(BASE_URL, '')
    create_dir(folder)

    # then dump files
    with open(folder + 'consoleText', 'w+') as f:
        f.write(consoleText)

    with open(folder + 'envVars', 'w+') as f:
        f.write(envVars)


def job_was_dumped(url):
    folder = OUTPUT_DIR + url.replace(BASE_URL, '')
    return os.path.exists(folder)


# DUMPERS ######################################################################
def dump_jobs(url):
    r = requests.get(url + '/api/json/', verify=False, auth=AUTH, timeout=20)
    if 'Authentication required' in r.text:
        print('[ERROR] This Jenkins needs authentication')
        exit(1)
    if 'Invalid password/token' in r.text:
        print('[ERROR] Invalid password/token for user')
        exit(1)
    if 'missing the Overall/Read permission' in r.text:
        print('[ERROR] User has no read permission')
        exit(1)

    response = json.loads(r.text)
    print_debug(response)
    parse_job(response, url)


def dump_build(url):
    r = requests.get(url + '/consoleText', verify=False, auth=AUTH)
    consoleText = r.text
    r = requests.get(url + '/injectedEnvVars/api/json', verify=False, auth=AUTH)
    envVars = r.text

    dump_to_disk(url, consoleText, envVars)


# PARSERS ######################################################################
def parse_job(response, url):
    if 'jobs' in response:
        for job in response['jobs']:
            print('[+] Found job {}'.format(job['name']))
            if RECOVER_FROM_FAILURE and job_was_dumped(job['url']):
                print('[-] Skipping job because of the configuration')
                continue
            try:
                dump_jobs(job['url'])
            except requests.exceptions.ReadTimeout:
                print('[ERROR] Gave up on job because of a timeout (server is probably busy)')

    if 'builds' in response:
        print('[+] Found {} builds'.format(len(response['builds'])))
        for build in response['builds']:
            dump_build(build['url'])
            if RECOVER_LAST_BUILD_ONLY == True:
                print('[-] Only recovering last build because of the configuration, use -f for a full dump')
                break


# MAIN #########################################################################
parser = argparse.ArgumentParser(description = 'Dump all available info from Jenkins')
parser.add_argument('url', nargs='+', type=str)
parser.add_argument('-u', '--user', type=str)
parser.add_argument('-p', '--password', type=str)
parser.add_argument('-o', '--output-dir', type=str)
parser.add_argument('-d', '--downgrade_ssl', action='store_true', help='Downgrade SSL to use RSA')
parser.add_argument('-f', '--full', action='store_true', help='Dump all available builds')
parser.add_argument('-r', '--recover_from_failure', action='store_true', help='Recover from server failure, skip all existing directories')

args = parser.parse_args()
if args.user and args.password:
    AUTH = (args.user, args.password)
else:
    AUTH = None
BASE_URL = args.url[0]
if args.output_dir:
    OUTPUT_DIR = args.output_dir + '/'
if args.downgrade_ssl:
    downgrade_ssl()
if args.full:
    RECOVER_LAST_BUILD_ONLY = False
if args.recover_from_failure:
    RECOVER_FROM_FAILURE = True

dump_jobs(BASE_URL)
