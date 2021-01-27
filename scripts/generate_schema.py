#!/usr/bin/env python

from argparse import ArgumentParser

from reiz.schema.builders import generate_schema


def main(argv=None):
    parser = ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("output_file")
    parser.add_argument("schema_file")

    generate_schema(**vars(parser.parse_args(argv)))


if __name__ == "__main__":
    main()
