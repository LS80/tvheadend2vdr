#! /usr/bin/env python

# Copyright 2015 Lee Smith
# Released under the MIT license


import os
import sys
import glob
import json
from collections import namedtuple
import argparse


TVH_PATH_GLOB = 'input/dvb/networks/*/muxes/*'

TVH_STREAM_TYPES = [
    ("H264", "MPEG2VIDEO"),
    ("AAC", "MPEG2AUDIO"),
    ("DVBSUB",)
]


Channel = namedtuple(
    'Channel',
    ['name', 'frequency', 'parameters', 'source', 'srate', 'vpid', 'apid',
     'tpid', 'ca', 'sid', 'nid', 'tid', 'rid']
)


def stream_pids(streams, stream_types):
    for stream in streams:
        if stream['type'] in stream_types:
            pid = stream['pid']
            yield str(pid)

     
def get_stream_pid(streams):
    for stream_types in TVH_STREAM_TYPES:
        pids = ','.join(stream_pids(streams, stream_types))
        yield pids if pids else '0'


def get_channel_config(conf, source, freq, nid, tid, params):
    vpid, apid, tpid = get_stream_pid(conf['stream'])
    
    name = "{};-".format(conf['svcname'])
    service_id = conf['sid']
    symbol_rate = ca = rid = 0

    return Channel(name, freq, params, source, symbol_rate, vpid,
                   apid, tpid, ca, service_id, nid, tid, rid)


def get_mux_config(conf):
    source = conf['delsys'][3]
    assert source in ('T', 'C', 'S')

    freq = conf['frequency']

    nid = conf['onid']
    tid = conf['tsid']

    params = {p: 0 for p in ('I', 'D', 'Y')}
    params['C'] = conf['fec_hi'].replace('/', '')
    params['M'] = conf['constellation'].split('/')[1]
    params['B'] = conf['bandwidth'][0]
    params['T'] = conf['transmission_mode'][0]
    params['G'] = conf['guard_interval'].split('/')[1]

    params = "I{I}C{C}D{D}G{G}M{M}B{B}T{T}Y{Y}".format(**params)

    return source, freq, nid, tid, params 


def get_channels_conf(user, config_path):
    path_glob = os.path.join(os.path.expanduser('~' + user), config_path, TVH_PATH_GLOB)

    for mux_path in glob.glob(path_glob):
        services_path = os.path.join(mux_path, 'services')
        if os.path.isdir(services_path):
            mux_config_path = os.path.join(mux_path, 'config')
            mux_config = get_mux_config(json.load(open(mux_config_path)))
            for channel_config_path in glob.glob(services_path + '/*'):
                yield get_channel_config(json.load(open(channel_config_path)),
                                         *mux_config)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Tvheadend channel configuration to VDR format')

    parser.add_argument('-u', '--user', default='hts',
                        help='set the Tvheadend user name (default: %(default)s)')

    parser.add_argument('-p', '--path', default='.hts/tvheadend',
                        help='set the Tvheadend config path relative to '
                             'the user home directory (default: %(default)s)')
                        
    parser.add_argument('-o', '--outfile', nargs='?', type=argparse.FileType('w'),
                        default=sys.stdout, const='channels.conf',
                        help='output to a file instead of stdout (default: %(const)s)')

    args = parser.parse_args()

    channels_conf = get_channels_conf(args.user, args.path)
    output = (':'.join(map(str, channel)) + '\n' for channel in channels_conf)
    
    try:
        args.outfile.writelines(output)
    except AttributeError:
        with open(args.outfile, 'w') as f:
            f.writelines(output)

if __name__ == "__main__":
    main()

