#! python


import getopt
import os
import sys
import time
from zlib import crc32

import MySQLdb
from pyAudioAnalysis import audioTrainTest as aT

from config import *
from noise_removal import noiseCleaner


def classify(directory=os.getcwd(), model_file=os.path.join(os.getcwd(), 'model'), classifierType='gradientboosting',
             verbose=False):
    for file in os.listdir(directory):
        if file.endswith('.wav'):
            file = os.path.join(directory, file)
            added = os.path.getmtime(file)
            added = time.gmtime(added)
            added = time.strftime('\'' + '-'.join(['%Y', '%m', '%d']) + ' ' + ':'.join(['%H', '%M', '%S']) + '\'',
                                  added)

            cleaner = noiseCleaner(verbose=verbose)
            clean_wav = cleaner.noise_removal(file)
            Result, P, classNames = aT.fileClassification(clean_wav, model_file, classifierType)

            result_dict = {}
            for i in xrange(0, len(classNames)):
                result_dict[classNames[i]] = P[i]

            result_dict = sorted(result_dict.items(), key=lambda x: x[1], reverse=True)

            sample_id = crc32(file)
            device_id = -1  # tbi
            latitude = -1  # tbi
            longitute = -1  # tbi
            humidity = -1  # tbi
            temp = -1  # tbi
            light = -1  # tbi
            type1 = '\'' + result_dict[0][0] + '\''
            type2 = '\'' + result_dict[1][0] + '\''
            type3 = '\'' + result_dict[2][0] + '\''
            per1 = result_dict[0][1]
            per2 = result_dict[1][1]
            per3 = result_dict[2][1]

            values = [sample_id, device_id, added, latitude, longitute, humidity, temp, light, type1, per1, type2, per2,
                      type3, per3]
            values = [str(x) for x in values]

            with MySQLdb.connect(host=host, user=user, passwd=passwd,
                                 db=database) as cur:  # config is in config.py: see above
                query_text = "INSERT INTO sampleInfo (sampleid, deviceid, added, latitude, longitude, humidity, temp, light, type1, per1, type2, per2, type3, per3) values(" + ','.join(
                    values) + ");"
                cur.execute(query_text)

    try:
        export_file = crc32(str(time.time()))
        if os.system("mysqldump -u %s -p %s --password=%s --skip-add-drop-table --no-create-info > export/%s.sql" % (
        user, database, passwd, export_file)):
            raise Exception("mysqldump export failed!")
    except:
        raise
    else:
        with MySQLdb.connect(host=host, user=user, passwd=passwd,
                             db=database) as cur:
            cur.execute("DROP DATABASE %s;" % database)
            cur.execute("CREATE DATABASE %s;" % database)

        parent_dir, current_subdir = os.path.split(os.getcwd())
        tbl_create = os.path.join(parent_dir, 'database', 'tbl_create.sql')
        if os.system("mysql -u %s -p %s --password=%s < %s" % (user, database, passwd, tbl_create)):
            raise Exception("tbl_create.sql error!")


if __name__ == '__main__':

    directory = os.getcwd()
    classifierType = 'gradientboosting'
    birds = []
    verbose = False
    model_file = os.path.join(directory, 'model')
    skip_clean = False
    no_sanitize = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:m:c:b:v",
                                   ["dir=", "model=", "classifier=", "verbose"])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)  # will print something like "option -a not recognized"
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-d", "--dir"):
            directory = arg
        elif opt in ("-m", "--model"):
            model_file = arg
        elif opt in ("-c", "--classifier"):
            classifierType = arg
        elif opt in ("-v", "--verbose"):
            verbose = True
        else:
            assert False, "unhandled option"

    if not os.path.isfile(model_file):
        raise Exception("Model file:" + model_file + " not found!")

    if classifierType not in ('knn', 'svm', 'gradientboosting', 'randomforest', 'extratrees'):
        raise Exception(classifierType + " is not a valid model type!")

    classify(directory, model_file, classifierType, verbose=verbose)