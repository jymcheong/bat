"""FileTailer Python Class"""
from __future__ import print_function
import os
import sys
import argparse
import time
import math
from collections import Counter

# Third Party Imports
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans

# Local imports
from brothon import bro_log_reader
from brothon.analysis import dataframe_to_matrix


if __name__ == '__main__':
    # Example to show the dataframe cache functionality on streaming data
    pd.set_option('display.width', 1000)

    # Collect args from the command line
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--bro-log', type=str, help='Specify a bro log to run BroLogReader test on')
    args, commands = parser.parse_known_args()

    # Check for unknown args
    if commands:
        print('Unrecognized args: %s' % commands)
        sys.exit(1)

    # If no args just call help
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # Sanity check that this is a dns log
    if not args.bro_log.endswith('dns.log'):
        print('This example only works with Bro dns.log files..')
        sys.exit(1)

    # File may have a tilde in it
    if args.bro_log:
        args.bro_log = os.path.expanduser(args.bro_log)

        # Create a Bro IDS log reader
        print('Opening Data File: {:s}'.format(args.bro_log))
        reader = bro_log_reader.BroLogReader(args.bro_log)

        # Create a Pandas dataframe from reader
        bro_df = pd.DataFrame(reader.readrows())
        print('Read in {:d} Rows...'.format(len(bro_df)))

        # Using Pandas we can easily and efficiently compute additional data metrics
        # Here we use the vectorized operations of Pandas/Numpy to compute query length
        bro_df['query_length'] = bro_df['query'].str.len()

        # Use the BroThon DataframeToMatrix class
        features = ['Z', 'rejected', 'proto', 'query', 'qclass_name', 'qtype_name', 'rcode_name', 'query_length']
        to_matrix = dataframe_to_matrix.DataFrameToMatrix()
        bro_matrix = to_matrix.fit_transform(bro_df[features])
        print(bro_matrix.shape)

        # Train/fit and Predict anomalous instances using the Isolation Forest model
        odd_clf = IsolationForest(contamination=0.35) # Marking 35% as odd
        odd_clf.fit(bro_matrix)

        # Add clustering to our outliers
        bro_df['cluster'] = KMeans(n_clusters=4).fit_predict(bro_matrix)

        # Now we create a new dataframe using the prediction from our classifier
        odd_df = bro_df[features+['cluster']][odd_clf.predict(bro_matrix) == -1]

        # Now group the dataframe by cluster
        cluster_groups = odd_df[features+['cluster']].groupby('cluster')

        # Now print out the details for each cluster
        print('<<< Outliers Detected! >>>')
        for key, group in cluster_groups:
            print('\nCluster {:d}: {:d} observations'.format(key, len(group)))
            print(group.head())
