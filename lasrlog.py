import argparse
import datetime
import io
import operator
import os
import platform
import sys
import textwrap
import time
from texttable import Texttable
from functools import reduce


def check_installation(version):
    current_version = sys.version_info
    if current_version[0] == version[0] and current_version[1] >= version[1]:
        pass
    else:
        sys.stderr.write(
            "[%s] - Error: Your Python interpreter must be %d.%d or greater (within major version %d)\n" % (
                sys.argv[0], version[0], version[1], version[0]))
        sys.exit(-1)
    return 0


check_installation((3, 0))


def _str_to_bool(s):
    return {'true': True, 'false': False}[s.lower()]


def _str_to_time(s):
    try:
        return datetime.datetime.strptime(s, "%m/%d/%y %H:%M:%S")
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid date/time: '{0}'.".format(s))


def in_range(start, end, x):
    if start <= end:
        return start <= x <= end
    else:
        return start <= x or x <= end


parser = argparse.ArgumentParser()
parser.add_argument("file", type=str, help="The path to actions file")
parser.add_argument("-c", "--howmany", type=int, default=10,
                    help="How many actions needs to be printed after sorting? By default 10.")
parser.add_argument("-s", "--sortby", type=str,
                    default="runtime",
                    choices=["id", "pid", "sastime", "time", "user", "rawcmd", "tablename", "statusmsg", "runtime"],
                    help="Sort by specific field. By default sorting by runtime. Possible values are:\nid, pid, sastime, time, user, rawcmd, tablename, statusmsg, runtime")
parser.add_argument("-r", "--reverse", type=_str_to_bool,
                    default=True, help="This is using to flag descending sorts (boolean value), by default True.")
parser.add_argument("-g", "--greaterthan", type=float, default=0,
                    help="Print actions with run time greater or equals specified value")
parser.add_argument("-t", "--tablename", type=str, default=None, help="")
parser.add_argument("-a", "--action", type=str, default=None, help="")
parser.add_argument("-u", "--user", type=str, default=None, help="")
parser.add_argument("-coloring", "--coloring", type=_str_to_bool, default=False, help="")
args = parser.parse_args()


class LASRAction(object):
    def __init__(self):
        self.id = None
        self.pid = None
        self.sastime = None
        self.time = None
        self.server_user = None
        self.server_host = None
        self.server_port = None
        self.user = ""
        self.rawcmd = None
        self.tablename = ""
        self.statusmsg = None
        self.runtime = None
        self.startline = None
        self.endline = None
        self.totallines = None


class Log(object):
    actions = []
    action = LASRAction()

    current_line = 0

    def __init__(self):
        pass

    def get_entries(self):
        if os.path.isfile(args.file):
            with io.open(args.file, encoding='utf-8-sig', errors='ignore') as f:
                for line in f:
                    self.current_line += 1

                    for item in line.split(','):
                        attr = item.split('=')

                        try:
                            if attr[0] == 'ID':
                                self.action = LASRAction()
                                self.action.id = int(attr[1])
                                self.action.startline = self.current_line

                            if attr[0] == 'PID':
                                self.action.pid = int(attr[1])

                            if attr[0] == 'SASTime':
                                self.action.sastime = attr[1]

                            if attr[0] == 'Time':
                                self.action.time = attr[1]

                            if attr[0] == 'User':
                                self.action.server_user = attr[1]

                            if attr[0] == 'Host':
                                self.action.server_host = attr[1]

                            if attr[0] == 'Port':
                                self.action.server_port = attr[1]

                            if attr[0] == 'RawCmd':
                                rawcmd = attr[2].split(' ')

                                if rawcmd[1] == '"name':
                                    self.action.tablename = attr[3].split('"')[0]

                                self.action.rawcmd = rawcmd[0]

                            if attr[0] == 'StatusMsg':
                                self.action.statusmsg = attr[1]

                            if attr[0].strip() == 'RunTime':
                                self.action.endline = self.current_line
                                self.action.totallines = (self.current_line - self.action.startline) + 1
                                self.action.runtime = float(attr[1].strip())

                                if self.action.runtime >= args.greaterthan:
                                    self.actions.append(self.action)

                            user_name_index = item.index("comment")
                            if user_name_index > 0:
                                self.action.user = item[user_name_index + 8:].split('"')[0]

                        except:
                            pass

                if len(self.actions) == 0:
                    print("Make sure that the file contains LASR actions...")
                    exit()


def main():
    is_lin = False
    is_mac = False
    is_win = False
    log_start_time = None
    log_end_time = None
    host = None
    user = None
    port = None

    if platform.system() == 'Linux':
        is_lin = True
    elif platform.system() == 'Darwin':
        is_mac = True
    elif platform.system() == 'Windows':
        is_win = True

    parsing_start_time = time.time()
    log = Log()
    log.get_entries()
    parsing_end_time = time.time()

    dt = datetime.datetime.strptime(log.actions[0].time, '%a %b %d %H:%M:%S %Y')
    log_start_time = '{:%m/%d/%Y %H:%M:%S}'.format(dt)
    dt = datetime.datetime.strptime(log.actions[len(log.actions) - 1].time, '%a %b %d %H:%M:%S %Y')
    log_end_time = '{:%m/%d/%Y %H:%M:%S}'.format(dt)

    sort_start_time = time.time()
    log.actions.sort(key=operator.attrgetter(args.sortby), reverse=args.reverse)
    sort_end_time = time.time()

    table = Texttable(0)
    table.set_deco(Texttable.HEADER)
    table.set_cols_dtype(['i', 't', 't', 't', 't', 't', 'f', 'i', 'i'])
    table.header(
        ['ID', 'Start Time', 'End Time', 'User', 'Raw Cmd', 'Table Name', 'Run time', 'Start Line', 'Total Lines'])

    for a in log.actions[:args.howmany]:
        runtime = None

        if user is None:
            user = a.server_user

        if host is None:
            host = a.server_host

        if port is None:
            port = a.server_port

        end_datetime_object = datetime.datetime.strptime(a.time, '%a %b %d %H:%M:%S %Y')
        start_datetime_object = end_datetime_object - datetime.timedelta(seconds=a.runtime)

        start_time = '{:%H:%M:%S}'.format(start_datetime_object)
        end_time = '{:%H:%M:%S}'.format(end_datetime_object)

        # if is_lin or is_mac or args.coloring:
        #     if in_range(0, 15, a.runtime):
        #         runtime = get_color_string(bcolors.GREEN, a.runtime)
        #     elif in_range(16, 30, a.runtime):
        #         runtime = get_color_string(bcolors.LIGHT_YELLOW, a.runtime)
        #     elif in_range(31, 60, a.runtime):
        #         runtime = get_color_string(bcolors.YELLOW, a.runtime)
        #     elif in_range(61, 2147483647, a.runtime):
        #         runtime = get_color_string(bcolors.RED, a.runtime)
        #     else:
        #         runtime = a.runtime

        #    table.add_row([a.id, start_time , end_time, a.user, a.rawcmd, a.tablename, a.runtime, a.startline, a.totallines])
        # else:

        # if args.tablename is not None:
        #    print(args.tablename)

        # if args.action is not None:
        #    print(args.action)

        # if args.user is not None:
        #    print(args.user)

        table.add_row([a.id, start_time, end_time, a.user, a.rawcmd, a.tablename, a.runtime, a.startline, a.totallines])

    print(table.draw())
    print("\nParse time:", "{0:.3f}".format(parsing_end_time - parsing_start_time))
    print("Sort time:", "{0:.3f}".format(sort_end_time - sort_start_time))
    print("Server Host: " + host)
    print("Server Port: " + port)
    print("Server User: " + user)
    print("Log Start Time: " + log_start_time)
    print("Log End Time: " + log_end_time)
    print("Total actions: " + str(len(log.actions)))


if __name__ == '__main__':
    main()
