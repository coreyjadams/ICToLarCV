import sys, os

import argparse
from Converter import Converter

def main():


    parser = argparse.ArgumentParser(description='IC file converter to larcv format')

    parser.add_argument('-i','--input',required=True,
                        dest='ic_fin',
                        help='Input IC file (Required)')

    parser.add_argument('-nevents','--num-events',
                        type=int, dest='nevents', default=None,
                        help='integer, Number of events to process (default all)')

    parser.add_argument('-o','--output',default=None,
                        type=str, dest='larcv_fout',
                        help='string,  Output larcv file name (optional)')

    args = parser.parse_args()



    c = Converter()
    c.convert(_file_in = args.ic_fin, _file_out=args.larcv_fout, max_entries=args.nevents)


if __name__ == '__main__':
    main()

