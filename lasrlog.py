import argparse
import datetime
import io
import operator
import os
import platform
import sys
import textwrap
from functools import reduce
from texttable import Texttable, get_color_string, bcolors

if sys.version_info[0] < 3:
    print("Error: Your Python interpreter must be version 3 or greater")
    exit()


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
parser.add_argument("-coloring", "--coloring", type=_str_to_bool, default=False, help="")
args = parser.parse_args()


class LASRAction(object):
    def __init__(self):
        self.id = None
        self.pid = None
        self.sastime = None
        self.time = None
        self.user = None
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
                                self.action.user = attr[1]

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
                        except:
                            pass

                if len(self.actions) == 0:
                    print("Make sure that the file contains LASR actions...")
                    exit()


def main():
    is_lin = False
    is_mac = False
    is_win = False

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

    sort_start_time = time.time()
    log.actions.sort(key=operator.attrgetter(args.sortby), reverse=args.reverse)
    sort_end_time = time.time()

    table = Texttable(0)
    table.set_deco(Texttable.HEADER)
    table.set_cols_dtype(['i', 't', 't', 't', 't', 'f', 'i', 'i'])
    table.header(['ID', 'Time', 'User', 'Raw Cmd', 'Table Name', 'Run time', 'Start Line', 'Total Lines'])
    for a in log.actions[:args.howmany]:
        runtime = None

        if is_lin or is_mac or args.coloring:
            if in_range(0, 15, a.runtime):
                runtime = get_color_string(bcolors.GREEN, a.runtime)
            elif in_range(16, 30, a.runtime):
                runtime = get_color_string(bcolors.LIGHT_YELLOW, a.runtime)
            elif in_range(31, 60, a.runtime):
                runtime = get_color_string(bcolors.YELLOW, a.runtime)
            elif in_range(61, 2147483647, a.runtime):
                runtime = get_color_string(bcolors.RED, a.runtime)
            else:
                runtime = a.runtime

            table.add_row([a.id, a.time, a.user, a.rawcmd, a.tablename, runtime, a.startline, a.totallines])
        else:
            table.add_row([a.id, a.time, a.user, a.rawcmd, a.tablename, a.runtime, a.startline, a.totallines])

    print(table.draw())
    print("\nParse time:", "{0:.3f}".format(parsing_end_time - parsing_start_time))
    print("Sort time:", "{0:.3f}".format(sort_end_time - sort_start_time))
    print("Total actions: " + str(len(log.actions)))


if __name__ == '__main__':
    main()
